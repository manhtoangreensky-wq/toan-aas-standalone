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
  // Telegram verification is asynchronous because the customer leaves the
  // Portal to confirm identity in the Bot. Poll only the same signed browser
  // session for the short one-time challenge lifetime; never poll a raw
  // Telegram ID or retain the code outside this in-memory page state.
  const TELEGRAM_CHALLENGE_POLL_INTERVAL_MS = 2500;
  const TELEGRAM_CHALLENGE_POLL_MAX_BACKOFF_MS = 10000;
  const TELEGRAM_CHALLENGE_MAX_MINUTES = 30;
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
  // Tier and scene selection belong to a quote/confirm boundary, not to the
  // minimum information needed for Bot planning. Keep this list explicit so
  // a future route cannot accidentally turn a draft into a browser-side
  // pricing decision.
  const TIERED_IMAGE_FEATURES = new Set([
    "image_create", "image_edit", "image_upscale", "image_transform", "image_remove_background"
  ]);
  const TIERED_VIDEO_FEATURES = new Set([
    "video_single", "video_product", "video_trend", "video_text_to_video", "video_quick",
    "video_image_to_video", "video_multiscene", "video_long"
  ]);
  const SINGLE_IMAGE_SOURCE_FEATURES = new Set([
    "image_edit", "image_upscale", "image_transform", "image_remove_background"
  ]);
  // These are Bot-owned quick commands with no browser-supplied arguments.
  // Keep the copy action allowlisted so a page/data attribute cannot turn the
  // Portal into a generic command or sensitive-text transport.
  const BOT_COMPANION_COMMANDS = new Set([
    "/notes", "/note", "/memory", "/reminders", "/remind", "/referral", "/ref",
    "/gift", "/promos", "/birthday", "/community", "/official_channels", "/menu", "/guide", "/help",
    "/film", "/image_tools", "/create_media", "/music", "/translate", "/doc_tools",
    "/growth_ai", "/campaign_report", "/language", "/mode", "/profile", "/mydata",
    "/tickets", "/ticket_status", "/data_delete"
  ]);
  // Analytics commands accept a deliberately tiny, fixed schema. Unlike the
  // zero-argument Bot companion commands above, this permits the customer to
  // choose a harmless report window/filter without turning the Portal into a
  // generic Telegram command transport or a second analytics/ledger writer.
  const ANALYTICS_BOT_COMMANDS = new Set(["/growth_ai", "/campaign_report"]);
  const ANALYTICS_BOT_PLATFORMS = new Set(["", "facebook", "tiktok", "youtube", "instagram", "threads", "website"]);
  const ANALYTICS_BOT_GOALS = new Set([
    "kiếm tiền affiliate", "tăng traffic", "tăng chuyển đổi", "tăng doanh thu", "tăng follow"
  ]);
  const CAMPAIGN_PLAN_PLATFORMS = new Set(["facebook", "instagram", "tiktok", "youtube", "website", "other"]);
  const CAMPAIGN_PLAN_OBJECTIVES = new Set(["affiliate", "traffic", "conversion", "revenue", "community"]);
  const CAMPAIGN_PLAN_STATUSES = new Set(["draft", "review", "approved", "scheduled", "archived"]);
  const ANALYTICS_BOT_FORMATS = new Set(["txt", "csv"]);
  const SUPPORT_SECRET_PATTERN = /\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|client[ _-]?secret|secret(?:[ _-]?key)?|password|passphrase|authorization)\b\s*(?:[:=]|\bis\b)\s*(?:bearer\s+)?[A-Za-z0-9_./+=:-]{8,}|\bbearer\s+[A-Za-z0-9._~+/=-]{12,}|\b(?:sk|pk|rk)_[A-Za-z0-9_-]{16,}|\b(?:otp|mã\s*xác\s*thực|ma\s*xac\s*thuc|cvv|cvc)\s*[:=]?\s*\d{3,8}\b/i;
  const SUPPORT_CARD_CANDIDATE_PATTERN = /\b(?:\d[ -]?){13,19}\b/g;
  const SUPPORT_MANUAL_PAYMENT_PROOF_PATTERN = /\b(?:txid|transaction(?:\s+(?:hash|id))?|mã\s*(?:giao\s*)?dịch|ma\s*(?:giao\s*)?dich|biên\s*lai|bien\s*lai|chứng\s*từ|chung\s*tu|bill|(?:số|so)\s*tài\s*khoản|bank\s*account|qr\s*(?:thanh\s*toán|payment|code)?)\b/i;
  let jobPollTimer = 0;
  let jobPollFailures = 0;
  let paymentPollTimer = 0;
  let paymentPollFailures = 0;
  let telegramLoginPollTimer = 0;
  let telegramLoginPollFailures = 0;
  let telegramLoginPollDeadline = 0;
  let telegramLoginResumeProbeInFlight = false;
  let telegramLinkPollTimer = 0;
  let telegramLinkPollFailures = 0;
  let telegramLinkPollDeadline = 0;
  let telegramLinkResumeProbeInFlight = false;
  const submissions = new Map();
  const FEATURE_BY_PATH = {
    "/chat": "chat", "/prompt-studio": "prompt_studio", "/content/caption": "caption",
    "/content/hashtag": "hashtag", "/content/hook": "hook", "/content/script": "script",
    "/content/storyboard": "storyboard", "/content/pack": "content_pack",
    "/image": "image_create", "/image/create": "image_create", "/image/edit": "image_edit", "/image/resize": "image_resize", "/image/upscale": "image_upscale", "/image/transform": "image_transform", "/image/remove-background": "image_remove_background", "/image/history": "image_history",
    "/video": "video_single", "/video/create": "video_single", "/video/long": "video_long", "/video/image-to-video": "video_image_to_video",
    "/video/product": "video_product", "/video/trend": "video_trend", "/video/multiscene": "video_multiscene", "/video/text-to-video": "video_text_to_video", "/video/quick": "video_quick", "/video/progress": "video_progress", "/video/preview": "video_preview", "/video/export": "video_export", "/video/add-ons": "video_addons", "/video/mux": "video_mux",
    "/voice": "voice_vault", "/voice/create": "voice_tts", "/voice/tts": "voice_tts", "/voice/vault": "voice_saved_tts", "/voice/saved": "voice_saved_tts", "/voice/clone": "voice_clone", "/voice/preview": "voice_preview", "/voice/outputs": "voice_outputs",
    "/music": "music_background", "/music/library": "music_library", "/music/sfx-library": "sfx_library", "/music/ai": "music_background", "/music/create": "music_background", "/music/song": "music_song", "/music/sfx": "music_sfx", "/music/upload": "music_upload",
    "/subtitle": "subtitle_asr", "/subtitle/create": "subtitle_create", "/translate": "subtitle_translate", "/dubbing": "video_dub", "/asr": "asr", "/subtitle/formats": "subtitle_formats", "/documents": "documents", "/documents/pdf": "documents_pdf", "/documents/ocr": "documents_ocr", "/documents/merge": "documents_merge", "/documents/split": "documents_split", "/documents/compress": "documents_compress", "/documents/image-to-pdf": "documents_image_to_pdf", "/documents/pdf-to-word": "documents_pdf_to_word", "/documents/translate": "documents_translate"
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
  // Only these module names have an explicit read-only branch in the current
  // Bot bridge. Do not turn every historical/admin command in the migration
  // inventory into a speculative `/admin/modules/<anything>` request: an
  // unknown compatibility page must remain a local guarded surface until the
  // Bot publishes a narrowly scoped read adapter for it.
  const ADMIN_CANONICAL_READ_MODULES = new Set([
    "overview", "summary", "users", "user", "wallet", "payments", "topups", "revenue", "refunds",
    "jobs", "failed-jobs", "workers", "runtime", "providers", "provider-cost", "features", "freezes",
    "pricing", "promos", "tickets", "support", "audit", "security", "reports", "system", "backups", "leads"
  ]);
  const ADMIN_MODULE_NAME_PATTERN = /^[a-z0-9][a-z0-9_-]{0,80}$/;

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
    // Every browser-generated write key must satisfy the exact server
    // contract: `[A-Za-z0-9._:-]{12,160}`. Submission scopes include routes
    // such as `/content/pack`, so using a scope verbatim leaked `/` into the
    // key and made otherwise valid Web-only draft saves fail server-side.
    const safePrefix = String(prefix || "web")
      .replace(/[^A-Za-z0-9._:-]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 120) || "web";
    return `${safePrefix}-${Array.from(bytes, (item) => item.toString(16).padStart(2, "0")).join("")}`;
  }

  function safeReturnPath(value) {
    if (typeof value !== "string") return "";
    const route = value.trim();
    if (!route || !route.startsWith("/") || route.startsWith("//") || route.includes("\\") || route.includes("\u0000") || route.includes("?") || route.includes("#")) return "";
    const normalized = route.replace(/\/+$/, "") || "/";
    return ["/login", "/register", "/onboarding"].includes(normalized) ? "" : normalized;
  }

  function requestedPortalRoute() {
    return safeReturnPath(new URLSearchParams(window.location.search).get("next") || "");
  }

  function telegramChallengePending(flow) {
    const data = flow && flow.data && typeof flow.data === "object" ? flow.data : {};
    return Boolean(
      flow
      && String(flow.status || "") === "awaiting_confirm"
      && (
        (typeof data.code === "string" && /^[A-Za-z0-9_-]{12,160}$/.test(data.code))
        // A refresh deliberately never restores the opaque code from browser
        // storage. The existing HttpOnly browser challenge can still be
        // polled safely by its recovered status marker.
        || data.recovered === true
      )
    );
  }

  function telegramChallengeDeadline(flow, previousDeadline) {
    if (previousDeadline && previousDeadline > Date.now()) return previousDeadline;
    const data = flow && flow.data && typeof flow.data === "object" ? flow.data : {};
    const declared = Number(data.expires_in_minutes);
    const minutes = Number.isFinite(declared)
      ? Math.max(1, Math.min(TELEGRAM_CHALLENGE_MAX_MINUTES, Math.floor(declared)))
      : 10;
    return Date.now() + (minutes * 60 * 1000);
  }

  function portalIsVisible() {
    return typeof document === "undefined" || document.visibilityState !== "hidden";
  }

  function currentPortalPath() {
    return (base().path || window.location.pathname || "/").split("?")[0];
  }

  function loginChallengeRoute() {
    return ["/login", "/register"].includes(currentPortalPath());
  }

  function linkChallengeRoute() {
    return ["/onboarding", "/account"].includes(currentPortalPath());
  }

  function stopTelegramLoginPolling() {
    if (telegramLoginPollTimer) window.clearTimeout(telegramLoginPollTimer);
    telegramLoginPollTimer = 0;
    telegramLoginPollFailures = 0;
    telegramLoginPollDeadline = 0;
  }

  function stopTelegramLinkPolling() {
    if (telegramLinkPollTimer) window.clearTimeout(telegramLinkPollTimer);
    telegramLinkPollTimer = 0;
    telegramLinkPollFailures = 0;
    telegramLinkPollDeadline = 0;
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
    if (SUPPORT_MANUAL_PAYMENT_PROOF_PATTERN.test(text)) {
      return "Nạp thủ công không nhận bill, TXID, số tài khoản hoặc QR trong Web App. Hãy mở Bot đã liên kết và dùng /thucong để đối soát an toàn.";
    }
    if (SUPPORT_SECRET_PATTERN.test(text) || candidates.some((item) => looksLikePaymentCard(item))) {
      return "Ticket không nhận API key, token, mật khẩu, OTP/CVV hoặc số thẻ. Hãy xóa dữ liệu nhạy cảm trước khi gửi.";
    }
    return "";
  }

  function adminBridgeTargetForPath(path) {
    const normalized = String(path || "/admin").split("?")[0];
    if (ADMIN_DIRECT_ENDPOINTS[normalized]) {
      return { endpoint: ADMIN_DIRECT_ENDPOINTS[normalized], module: normalized === "/admin" ? "overview" : normalized.split("/").filter(Boolean).slice(-1)[0], supported: true };
    }
    const pieces = normalized.split("/").filter(Boolean);
    const rawModule = String(pieces[1] || "overview").toLowerCase().replace(/_/g, "-");
    const requestedModule = ADMIN_MODULE_NAME_PATTERN.test(rawModule) ? rawModule : "compatibility";
    const module = ADMIN_MODULE_ALIASES[requestedModule] || requestedModule;
    const recordId = pieces.length > 2 ? pieces.slice(2).join("/") : "";
    if (!ADMIN_CANONICAL_READ_MODULES.has(module)) {
      return { endpoint: "", module, requestedModule, recordId: "", supported: false };
    }
    return {
      endpoint: `/admin/modules/${encodeURIComponent(module)}${recordId ? `?record_id=${encodeURIComponent(recordId)}` : ""}`,
      module,
      requestedModule,
      recordId,
      supported: true
    };
  }

  function localAdminCompatibilityGuard(target) {
    const module = String(target && target.module || "compatibility").slice(0, 81);
    return {
      ok: false,
      status: "guarded",
      message: "Module quản trị này đã được định tuyến từ Bot nhưng chưa có adapter Web canonical. Web giữ chế độ chỉ đọc, không gọi provider, Xu, PayOS hay workflow quản trị thay thế.",
      data: {
        module,
        items: [],
        read_only: true,
        compatibility_guarded: true,
        message: "Bot chưa công bố adapter read-only/write đã xác minh cho module này. Hãy tiếp tục workflow quản trị trong Bot canonical."
      },
      error_code: "ADMIN_MODULE_ADAPTER_NOT_PUBLISHED"
    };
  }

  async function readAdminPath(path) {
    const target = adminBridgeTargetForPath(path);
    return target.supported ? api(target.endpoint) : localAdminCompatibilityGuard(target);
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

  async function copyTelegramLinkCommand(value) {
    // The fallback command carries only a short-lived, opaque Web challenge.
    // It never contains a Telegram ID, session cookie, bridge credential or
    // any payment/provider data. The Bot still proves the caller identity.
    const command = String(value || "").trim();
    if (!/^\/linkweb\s+[A-Za-z0-9_-]{12,160}$/.test(command)) {
      throw new Error("Lệnh liên kết Telegram không hợp lệ.");
    }
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

  async function copyBotCompanionCommand(value) {
    const command = String(value || "").trim();
    if (!BOT_COMPANION_COMMANDS.has(command)) {
      throw new Error("Lệnh Bot companion không hợp lệ.");
    }
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

  function analyticsPositiveInteger(value, name, fallback) {
    const raw = String(value === undefined || value === null ? "" : value).trim();
    if (!raw && fallback !== undefined) return fallback;
    if (!/^\d{1,10}$/.test(raw)) throw new Error(`${name} không hợp lệ.`);
    const number = Number(raw);
    if (!Number.isSafeInteger(number) || number < 1 || number > 2147483647) throw new Error(`${name} không hợp lệ.`);
    return number;
  }

  function buildAnalyticsBotCommand(fields) {
    const values = fields && typeof fields === "object" ? fields : {};
    const baseCommand = String(values.bot_command || "").trim();
    if (!ANALYTICS_BOT_COMMANDS.has(baseCommand)) throw new Error("Lệnh analytics Bot không hợp lệ.");
    const defaultDays = baseCommand === "/growth_ai" ? 14 : 30;
    const days = analyticsPositiveInteger(values.days, "Số ngày", defaultDays);
    if (days > 90) throw new Error("Số ngày phải từ 1 đến 90.");
    const platform = String(values.platform || "").trim().toLowerCase();
    if (!ANALYTICS_BOT_PLATFORMS.has(platform)) throw new Error("Nền tảng analytics không hợp lệ.");
    const campaignValue = String(values.campaign_id === undefined || values.campaign_id === null ? "" : values.campaign_id).trim();
    const campaignId = campaignValue ? analyticsPositiveInteger(campaignValue, "Campaign ID") : 0;
    const parts = [baseCommand, `days=${days}`];
    if (platform) parts.push(`platform=${platform}`);
    if (campaignId) parts.push(`campaign_id=${campaignId}`);
    if (baseCommand === "/growth_ai") {
      const goal = String(values.goal || "kiếm tiền affiliate").trim();
      if (!ANALYTICS_BOT_GOALS.has(goal)) throw new Error("Mục tiêu Growth AI không hợp lệ.");
      // Goals above are a closed, reviewed set and contain no quote/newline;
      // quote it only because Bot's key/value parser preserves spaces.
      parts.push(`goal="${goal}"`);
    } else {
      const format = String(values.format || "txt").trim().toLowerCase();
      if (!ANALYTICS_BOT_FORMATS.has(format)) throw new Error("Định dạng report không hợp lệ.");
      parts.push(`format=${format}`);
    }
    return parts.join(" ");
  }

  async function copyAnalyticsBotCommand(fields) {
    const command = buildAnalyticsBotCommand(fields);
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(command);
      return command;
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
    return command;
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

  function discardSubmission(scope, entry) {
    // Preserve an idempotency key only while the browser cannot tell whether
    // its request reached the server.  Once a response is acknowledged, a
    // later deliberate admin action must receive a new canonical intent.
    if (entry && submissions.get(scope) === entry) submissions.delete(scope);
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

  function replacingSingleImageSource(route, fields) {
    const feature = FEATURE_BY_PATH[route];
    return SINGLE_IMAGE_SOURCE_FEATURES.has(feature) && selectedFiles(fields).length > 0;
  }

  function extensionOf(item) {
    const name = String((item && (item.name || item.file_name)) || "").toLowerCase();
    const index = name.lastIndexOf(".");
    return index >= 0 ? name.slice(index) : "";
  }

  function uploadItemsFor(route, fields) {
    const selected = selectedFiles(fields);
    // A new source image supersedes the stale staged source from the earlier
    // draft. Keeping both could let a JPG hide a previous non-image upload
    // from browser preflight even though the future adapter must receive one
    // unambiguous source asset.
    if (replacingSingleImageSource(route, fields)) return selected;
    const flow = priorFeatureFlow(route);
    const staged = flow.data && Array.isArray(flow.data.uploads) ? flow.data.uploads : [];
    return [...selected, ...staged.filter((item) => item && typeof item === "object")];
  }

  function uploadCountFor(route, fields) {
    if (replacingSingleImageSource(route, fields)) return selectedFiles(fields).length;
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

  function wholeNumberInRange(value, minimum, maximum) {
    const parsed = Number(value);
    return Number.isInteger(parsed) && parsed >= minimum && parsed <= maximum;
  }

  function scalarField(fields, route, name) {
    if (Object.prototype.hasOwnProperty.call(fields || {}, name)) return fields[name];
    const flow = priorFeatureFlow(route);
    return flow.input && typeof flow.input === "object" ? flow.input[name] : "";
  }

  function validateFeatureIntake(feature, route, fields, phase) {
    const files = uploadItemsFor(route, fields);
    const fileCount = uploadCountFor(route, fields);
    const action = ["draft", "estimate", "confirm"].includes(String(phase || "")) ? String(phase) : "draft";
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
      const operation = operationByFeature[feature] || String(scalarField(fields, route, "operation") || "pdf_to_images");
      if (operation === "image_to_pdf" && files.length && !allExtensionsMatch(files, images)) return "Image-to-PDF chỉ nhận JPG, PNG hoặc WebP.";
      if (["pdf_to_images", "merge_pdf", "split_pdf", "compress_pdf", "ocr_pdf"].includes(operation) && files.length && !allExtensionsMatch(files, pdf)) return "Thao tác này chỉ nhận tệp PDF.";
      if (operation === "ocr_image" && files.length && !anyExtensionMatches(files, images)) return "OCR ảnh chỉ nhận JPG, PNG hoặc WebP.";
      if (operation === "merge_pdf" && fileCount < 2) return "Gộp PDF cần ít nhất hai tệp đã vào staging canonical.";
      if (operation === "split_pdf" && !/^\d+(?:-\d+)?$/.test(String(scalarField(fields, route, "page_range") || "").trim())) return "Khoảng trang phải là một trang hoặc dải liên tiếp, ví dụ 2 hoặc 2-5.";
      if (operation === "translate_document" && !CANONICAL_TARGET_LANGUAGE_CODES.has(language)) return "Hãy chọn ngôn ngữ đích canonical cho tài liệu từ danh sách Bot P0 hỗ trợ.";
    }
    if (["image_edit", "image_upscale", "image_transform", "image_remove_background"].includes(feature)) {
      if (fileCount !== 1) return "Workflow ảnh này cần đúng một ảnh nguồn đã vào staging canonical.";
      if (!allExtensionsMatch(files, images)) return "Workflow ảnh này chỉ nhận đúng một tệp JPG, PNG hoặc WebP.";
    }
    if (feature === "video_image_to_video") {
      if (!fileCount) return "Image-to-Video cần ảnh nguồn đã vào staging canonical.";
      if (files.length && !anyExtensionMatches(files, images)) return "Image-to-Video chỉ nhận JPG, PNG hoặc WebP.";
    }
    if (feature === "voice_saved_tts" && !String(scalarField(fields, route, "voice_profile_id") || "").trim()) return "Hãy chọn một giọng Voice Vault đã sẵn sàng.";
    if (feature === "video_dub") {
      const speed = Number(scalarField(fields, route, "speed") || "");
      if (!Number.isFinite(speed) || speed < 0.7 || speed > 1.8) return "Tốc độ dubbing phải là giá trị canonical từ 0.7× đến 1.8×.";
    }
    if (action === "confirm" && (TIERED_IMAGE_FEATURES.has(feature) || TIERED_VIDEO_FEATURES.has(feature))) {
      if (!String(scalarField(fields, route, "tier") || "").trim()) return "Hãy chọn tier canonical rồi ước tính lại trước khi xác nhận.";
    }
    if (action === "confirm" && TIERED_VIDEO_FEATURES.has(feature) && !wholeNumberInRange(scalarField(fields, route, "scene_count"), 1, 20)) {
      return "Video cần số cảnh nguyên từ 1 đến 20 trước khi xác nhận job canonical.";
    }
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
          const jobId = jobIdFromPath(path);
          if (!jobId) return;
          const [result, assets] = await Promise.all([
            api(`/jobs/${encodeURIComponent(jobId)}`),
            api("/assets").catch(() => ({ data: { items: [] } }))
          ]);
          const record = exactJobRecord(result.data, jobId);
          merge({
            jobDetail: record,
            jobAssets: ownedAssetsForJob(record, assets.data && assets.data.items),
            pageStates: { ...(base().pageStates || {}), [path]: result.status || "read_only" }
          });
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

  function validJobRecordId(value) {
    return /^[A-Za-z0-9._:-]{1,160}$/.test(String(value || "").trim());
  }

  function jobIdFromPath(path) {
    const raw = String(path || "");
    if (!raw.startsWith("/jobs/")) return "";
    try {
      const value = decodeURIComponent(raw.slice("/jobs/".length));
      return validJobRecordId(value) ? value : "";
    } catch (_) {
      return "";
    }
  }

  function ownedAssetsForJob(job, items) {
    const jobId = String(job && job.id || "").trim();
    if (!validJobRecordId(jobId) || !Array.isArray(items)) return [];
    return items
      .filter((item) => item && typeof item === "object" && String(item.id || "").trim() === jobId && validJobRecordId(item.id))
      .slice(0, 12)
      .map((item) => ({
        id: jobId,
        feature: typeof item.feature === "string" ? item.feature.slice(0, 160) : "",
        status: typeof item.status === "string" ? item.status.slice(0, 80) : "guarded",
        created_at: typeof item.created_at === "string" ? item.created_at.slice(0, 160) : "",
        output_available: item.output_available === true,
        download_ready: item.download_ready === true,
        delivery_ready: item.delivery_ready === true
      }));
  }

  function exactJobRecord(value, expectedId) {
    const record = value && typeof value === "object" ? value : {};
    const id = String(record.id || "").trim();
    return validJobRecordId(expectedId) && id === expectedId ? record : {};
  }

  function validAdminFeatureKey(value) {
    return /^[a-z][a-z0-9_]{1,120}$/.test(String(value || "").trim());
  }

  function validAdminJobId(value) {
    return /^[A-Za-z0-9._:-]{1,160}$/.test(String(value || "").trim());
  }

  function validWebQuoteReceipt(value) {
    return /^[A-Za-z0-9_-]{32,160}$/.test(String(value || "").trim());
  }

  function validCampaignPlanId(value) {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || "").trim());
  }

  function validProjectId(value) {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || "").trim());
  }

  function validVaultAssetId(value) {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || "").trim());
  }

  function validDocumentOperationId(value) {
    return validVaultAssetId(value);
  }

  function validImageOperationId(value) {
    return validVaultAssetId(value);
  }

  function validProjectPackageId(value) {
    return validProjectId(value);
  }

  function validWorkspaceDraftId(value) {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || "").trim());
  }

  function workspaceDraftFeatureForRoute(route) {
    const normalized = String(route || "").split("?")[0].replace(/\/+$/, "") || "/";
    const catalog = Array.isArray(base().catalog) ? base().catalog : [];
    const item = catalog.find((candidate) => candidate && typeof candidate.key === "string" && String(candidate.route || "").split("?")[0].replace(/\/+$/, "") === normalized);
    return item && item.web_workspace_draft_supported === true && /^[a-z][a-z0-9_]{1,120}$/.test(String(item.key || "")) ? item : null;
  }

  function workspaceDraftInput(fields) {
    const forbidden = new Set(["upload_ids", "upload_id", "source", "sample", "audio", "document", "documents", "file", "files", "attachment", "voice_profile_id", "web_quote_receipt", "quote_receipt", "idempotency_key", "consent"]);
    const result = {};
    Object.entries(fields && typeof fields === "object" ? fields : {}).forEach(([name, value]) => {
      if (!/^[a-z][a-z0-9_]{0,63}$/.test(name) || forbidden.has(name) || typeof value !== "string") return;
      const text = value.trim();
      if (text && text.length <= 4000) result[name] = text;
    });
    return result;
  }

  function mergeWorkspaceDraft(item) {
    if (!item || typeof item !== "object" || !validWorkspaceDraftId(item.id)) return;
    const current = Array.isArray(base().workspaceDrafts) ? base().workspaceDrafts : [];
    merge({ workspaceDrafts: [item, ...current.filter((candidate) => !candidate || String(candidate.id || "") !== String(item.id))].slice(0, 100) });
  }

  function campaignPlanIdFromPath(path) {
    const match = /^\/campaigns\/([^/]+)$/.exec(String(path || "").split("?")[0]);
    const id = match ? String(match[1] || "") : "";
    return validCampaignPlanId(id) ? id : "";
  }

  function projectIdFromPath(path) {
    const match = /^\/projects\/([^/]+)$/.exec(String(path || "").split("?")[0]);
    const id = match ? String(match[1] || "") : "";
    return validProjectId(id) ? id : "";
  }

  function normalizeCampaignSchedule(value) {
    const raw = String(value || "").trim();
    if (!raw) return "";
    // `datetime-local` intentionally sends a timezone-free planning marker.
    // It is not an automation schedule and the server refuses offset/Z forms.
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?$/.test(raw)) throw new Error("Mốc lịch cần ở định dạng ngày giờ cục bộ hợp lệ.");
    const parsed = new Date(raw);
    if (Number.isNaN(parsed.getTime())) throw new Error("Mốc lịch cần ở định dạng ngày giờ cục bộ hợp lệ.");
    return raw;
  }

  function campaignCreatePayload(fields) {
    const title = String(fields.title || "").replace(/\s+/g, " ").trim();
    if (title.length < 3 || title.length > 180) throw new Error("Tên kế hoạch cần từ 3 đến 180 ký tự.");
    let destination;
    try { destination = new URL(String(fields.destination_url || "").trim()); } catch (_) { throw new Error("Liên kết đích HTTPS không hợp lệ."); }
    if (destination.protocol !== "https:" || !destination.hostname || destination.username || destination.password || (destination.port && destination.port !== "443")) {
      throw new Error("Liên kết đích phải là HTTPS công khai, không kèm thông tin đăng nhập.");
    }
    const platform = String(fields.platform || "").trim().toLowerCase();
    const objective = String(fields.objective || "").trim().toLowerCase();
    if (!CAMPAIGN_PLAN_PLATFORMS.has(platform)) throw new Error("Hãy chọn nền tảng kế hoạch hợp lệ.");
    if (!CAMPAIGN_PLAN_OBJECTIVES.has(objective)) throw new Error("Hãy chọn mục tiêu kế hoạch hợp lệ.");
    return { title, destination_url: destination.href, platform, objective, scheduled_for: normalizeCampaignSchedule(fields.scheduled_for) };
  }

  function campaignStatusPayload(fields) {
    const planId = String(fields.plan_id || "").trim();
    const approvalStatus = String(fields.approval_status || "").trim().toLowerCase();
    const reviewNote = String(fields.review_note || "").replace(/\s+/g, " ").trim();
    if (!validCampaignPlanId(planId)) throw new Error("Mã kế hoạch không hợp lệ.");
    if (!CAMPAIGN_PLAN_STATUSES.has(approvalStatus)) throw new Error("Trạng thái kế hoạch không hợp lệ.");
    if (reviewNote.length > 1000) throw new Error("Ghi chú tự rà soát tối đa 1000 ký tự.");
    return { plan_id: planId, approval_status: approvalStatus, review_note: reviewNote };
  }

  function mergeCampaignPlan(item) {
    if (!item || typeof item !== "object" || !validCampaignPlanId(item.id)) return;
    const current = Array.isArray(base().campaignPlans) ? base().campaignPlans : [];
    const next = [item, ...current.filter((candidate) => !candidate || String(candidate.id || "") !== String(item.id))].slice(0, 100);
    const activePlanId = campaignPlanIdFromPath((base().path || window.location.pathname).split("?")[0]);
    const update = { campaignPlans: next };
    if (activePlanId && activePlanId === String(item.id)) update.campaignPlanDetail = item;
    merge(update);
  }

  function estimateCanAdvanceToConfirm(estimate) {
    return Boolean(
      estimate
      && typeof estimate === "object"
      && estimate.available === true
      && estimate.tier_required !== true
      && estimate.scene_count_required !== true
    );
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

  function safeFeatureExecutionFeatures(value) {
    const known = new Set(Object.values(FEATURE_BY_PATH));
    if (!Array.isArray(value)) return [];
    return [...new Set(value.filter((feature) => typeof feature === "string" && known.has(feature)))].slice(0, 200);
  }

  function featureExecutionAllowed(feature) {
    const bridge = base().bridge && typeof base().bridge === "object" ? base().bridge : {};
    const features = safeFeatureExecutionFeatures(bridge.featureExecutionFeatures);
    return Boolean(
      typeof feature === "string"
      && features.includes(feature)
      && bridge.featureExecutionAvailable === true
      && base().capabilities && base().capabilities["feature-confirm"] === true
    );
  }

  function featurePageStates(catalog, readiness, executionFeatures, workspaceDraftFeatures, webAuthoringAvailable) {
    const states = {};
    const features = (readiness && readiness.features) || {};
    const allowed = new Set(safeFeatureExecutionFeatures(executionFeatures));
    const current = base();
    const draftFeatures = new Set(Array.isArray(workspaceDraftFeatures)
      ? workspaceDraftFeatures
      : (Array.isArray(current.workspaceDraftFeatures) ? current.workspaceDraftFeatures : []));
    const authoringReady = webAuthoringAvailable === true || Boolean(
      current.session && current.session.authenticated === true
      && current.session.csrfReady === true
      && current.capabilities && current.capabilities["workspace-draft-save"] === true
    );
    const stateForFeature = (route, key) => {
      if (typeof route !== "string" || !route || typeof key !== "string" || !key) return;
      const state = features[key];
      const executionReady = Boolean(state && state.public_ready && allowed.has(key));
      const draftReady = Boolean(authoringReady && draftFeatures.has(key));
      if (!state && !draftReady) return;
      states[route] = executionReady || draftReady ? "ready" : "guarded";
    };
    Object.entries(FEATURE_BY_PATH).forEach(([route, key]) => {
      stateForFeature(route, key);
    });
    (catalog || []).forEach((item) => {
      if (!item || typeof item.key !== "string") return;
      stateForFeature(item.route && item.route.split("?")[0], item.key);
    });
    return states;
  }

  function safeOAuthStartPath(value) {
    if (typeof value !== "string" || !value) return "";
    try {
      const url = new URL(value, window.location.origin);
      if (url.origin !== window.location.origin) return "";
      return /^\/api\/v1\/auth\/oauth\/(telegram|google|github|apple)\/start$/.test(url.pathname) && url.searchParams.get("link") === "1" ? `${url.pathname}?link=1` : "";
    } catch (_) {
      return "";
    }
  }

  function telegramConnectionReady(connection) {
    return Boolean(
      connection
      // `ready` is issued only after the Web receiver is configured *and*
      // an operator has explicitly enabled the separately deployed Bot link
      // adapter.  Do not recreate the older two-boolean check here: it let a
      // Web-only deploy mint codes which the running Bot could not consume.
      && connection.ready === true
    );
  }

  async function hydrate() {
    const context = base();
    const [catalogResponse, statusResponse, meResponse, providerResponse, telegramConnectionResponse] = await Promise.all([
      fetch(`${API}/catalog`, { credentials: "same-origin" }).then((r) => r.json()).catch(() => ({})),
      fetch(`${API}/core/status`, { credentials: "same-origin" }).then((r) => r.json()).catch(() => ({})),
      fetch(`${API}/auth/me`, { credentials: "same-origin" }).then(async (r) => r.ok ? r.json() : ({})).catch(() => ({})),
      fetch(`${API}/auth/providers`, { credentials: "same-origin" }).then((r) => r.json()).catch(() => ({})),
      fetch(`${API}/auth/telegram/connection/status`, { credentials: "same-origin" }).then((r) => r.json()).catch(() => ({}))
    ]);
    const catalog = catalogResponse && catalogResponse.data && Array.isArray(catalogResponse.data.features) ? catalogResponse.data.features : [];
    const webWorkspaceDraftFeatures = [...new Set(catalog
      .filter((item) => item && item.web_workspace_draft_supported === true && /^[a-z][a-z0-9_]{1,120}$/.test(String(item.key || "")))
      .map((item) => String(item.key)))].slice(0, 200);
    const status = statusResponse && statusResponse.data ? statusResponse.data : {};
    const me = meResponse && meResponse.data ? meResponse.data : {};
    const oauthProviders = providerResponse && providerResponse.data && providerResponse.data.providers && typeof providerResponse.data.providers === "object" ? providerResponse.data.providers : {};
    const telegramConnection = telegramConnectionResponse && telegramConnectionResponse.data && typeof telegramConnectionResponse.data === "object" ? telegramConnectionResponse.data : {};
    const telegramReady = telegramConnectionReady(telegramConnection);
    const account = me.account || null;
    const accountDisplayName = account
      ? (account.display_name || account.email || (account.account_type === "telegram" ? "Người dùng Telegram" : "Khách"))
      : "";
    const copyfastEnabled = Boolean(status.flags && status.flags.copyfast_enabled);
    const assetVaultEnabled = Boolean(status.flags && status.flags.asset_vault_enabled === true);
    const projectPackageEnabled = Boolean(status.flags && status.flags.project_package_enabled === true);
    const documentOperationsEnabled = Boolean(status.flags && status.flags.document_operations_enabled === true);
    const imageToPdfEnabled = Boolean(status.flags && status.flags.image_to_pdf_enabled === true);
    const pdfToWordEnabled = Boolean(status.flags && status.flags.pdf_to_word_enabled === true);
    const imageOperationsEnabled = Boolean(status.flags && status.flags.image_operations_enabled === true);
    const imageResizeEnabled = Boolean(status.flags && status.flags.image_resize_enabled === true);
    // This native page must never display the static catalog's `ready` badge
    // while its server-side execution gate is intentionally off.
    const nativeDocumentPageStates = {
      "/documents/image-to-pdf": account && assetVaultEnabled && documentOperationsEnabled && imageToPdfEnabled ? "ready" : "guarded",
      "/documents/pdf-to-word": account && assetVaultEnabled && documentOperationsEnabled && pdfToWordEnabled ? "ready" : "guarded"
    };
    const nativeImagePageStates = {
      // The private source/history reads still need to complete before a
      // server-enabled native page can truthfully show a ready badge.
      "/image/resize": account && assetVaultEnabled && imageOperationsEnabled && imageResizeEnabled ? "processing" : "guarded"
    };
    const telegramLinked = Boolean(account && account.telegram_linked);
    const bridgeAvailable = Boolean(copyfastEnabled && status.bridge_configured && telegramLinked);
    const webFeatureExecutionFeatures = safeFeatureExecutionFeatures(status.web_feature_execution_features);
    const webFeatureExecutionAvailable = Boolean(
      bridgeAvailable
      && status.flags && status.flags.provider_calls_enabled
      && status.web_feature_execution_available === true
      && webFeatureExecutionFeatures.length > 0
    );
    const adminWriteEnabled = Boolean(
      status.flags && status.flags.admin_erp_enabled === true
      && status.flags.admin_writes_enabled === true
      && account && account.role === "admin" && me.csrf_token && bridgeAvailable
    );
    const capabilities = {
      "auth-login": true,
      "auth-register": true,
      "start-telegram-login": telegramReady,
      "refresh-telegram-login": true,
      "start-oauth-telegram": Boolean(oauthProviders.telegram && oauthProviders.telegram.enabled === true),
      "start-oauth-google": Boolean(oauthProviders.google && oauthProviders.google.enabled === true),
      "start-oauth-github": Boolean(oauthProviders.github && oauthProviders.github.enabled === true),
      "start-oauth-apple": Boolean(oauthProviders.apple && oauthProviders.apple.enabled === true),
      "link-oauth-telegram": Boolean(account && me.csrf_token && oauthProviders.telegram && oauthProviders.telegram.enabled === true),
      "link-oauth-google": Boolean(account && me.csrf_token && oauthProviders.google && oauthProviders.google.enabled === true),
      "link-oauth-github": Boolean(account && me.csrf_token && oauthProviders.github && oauthProviders.github.enabled === true),
      "link-oauth-apple": Boolean(account && me.csrf_token && oauthProviders.apple && oauthProviders.apple.enabled === true),
      "update-profile": Boolean(account && me.csrf_token),
      "auth-logout": Boolean(account && me.csrf_token),
      // Web-owned Campaign Planner writes require only a signed Web session
      // and CSRF. They do not imply that a Telegram/Core Bridge/provider
      // adapter is available and never publish or create canonical state.
      "campaign-create": Boolean(account && me.csrf_token),
      "campaign-update": Boolean(account && me.csrf_token),
      "campaign-update-status": Boolean(account && me.csrf_token),
      "upgrade-telegram-account": Boolean(account && me.csrf_token && account.account_type === "telegram" && account.login_methods && account.login_methods.email !== true),
      "start-telegram-link": Boolean(account && telegramReady),
      "refresh-link-status": Boolean(account),
      // Account Activity is a Web-owned, signed-session read. It has no
      // Core Bridge dependency and never exposes the raw audit record.
      "refresh-account-activity": Boolean(account),
      "workspace-draft-save": Boolean(account && me.csrf_token),
      "workspace-draft-archive": Boolean(account && me.csrf_token),
      "workspace-draft-resume": Boolean(account),
      "workspace-drafts-refresh": Boolean(account),
      // Project Center is independently owned by the signed Web account.
      // Telegram/Bot availability must never gate authoring, version history
      // or owner-scoped project reads.
      "project-create": Boolean(account && me.csrf_token),
      "project-update": Boolean(account && me.csrf_token),
      "projects-refresh": Boolean(account),
      "studio-document-create": Boolean(account && me.csrf_token),
      "studio-document-open": Boolean(account),
      "studio-document-update": Boolean(account && me.csrf_token),
      "studio-document-restore": Boolean(account && me.csrf_token),
      // Project Packages are a separate Web-native artifact pipeline. They
      // require signed session + CSRF + a dedicated persistent storage root,
      // never Telegram, bridge, wallet, PayOS or provider availability.
      "project-package-view": Boolean(account && projectPackageEnabled),
      "project-package-export": Boolean(account && me.csrf_token && projectPackageEnabled),
      "project-package-refresh": Boolean(account && projectPackageEnabled),
      // The private vault is a native Web capability. It never needs a Bot
      // bridge or a Telegram link, but stays disabled until the server has a
      // dedicated persistent storage boundary.
      "asset-vault-view": Boolean(account && assetVaultEnabled),
      "asset-vault-upload": Boolean(account && me.csrf_token && assetVaultEnabled),
      "asset-vault-archive": Boolean(account && me.csrf_token && assetVaultEnabled),
      "asset-vault-refresh": Boolean(account && assetVaultEnabled),
      // PDF Split/Merge/Optimize are Web-native, storage-isolated operations. They require
      // only the signed Web account, CSRF and both local storage contracts;
      // no Telegram link, Bot bridge, provider, wallet or payment state.
      "document-operation-view": Boolean(account && assetVaultEnabled && documentOperationsEnabled),
      "document-operation-pdf-split": Boolean(account && me.csrf_token && assetVaultEnabled && documentOperationsEnabled),
      "document-operation-pdf-merge": Boolean(account && me.csrf_token && assetVaultEnabled && documentOperationsEnabled),
      "document-operation-pdf-optimize": Boolean(account && me.csrf_token && assetVaultEnabled && documentOperationsEnabled),
      "document-operation-image-to-pdf": Boolean(account && me.csrf_token && assetVaultEnabled && documentOperationsEnabled && imageToPdfEnabled),
      "document-operation-pdf-to-word": Boolean(account && me.csrf_token && assetVaultEnabled && documentOperationsEnabled && pdfToWordEnabled),
      "document-operation-refresh": Boolean(account && assetVaultEnabled && documentOperationsEnabled),
      // Resize & Aspect Studio is a separate Web-native image contract. It
      // needs no Telegram link/Core Bridge/provider/wallet, but remains
      // guarded until its own isolated storage and narrow decoder flag exist.
      "image-operation-view": Boolean(account && assetVaultEnabled && imageOperationsEnabled),
      "image-operation-resize": Boolean(account && me.csrf_token && assetVaultEnabled && imageOperationsEnabled && imageResizeEnabled),
      "image-operation-refresh": Boolean(account && assetVaultEnabled && imageOperationsEnabled),
      "refresh-jobs": Boolean(bridgeAvailable),
      "refresh-assets": Boolean(bridgeAvailable),
      "refresh-payment": Boolean(bridgeAvailable),
      "refresh-wallet-after-bot": Boolean(bridgeAvailable),
      "payment-lookup": Boolean(bridgeAvailable),
      "refresh-admin": Boolean(status.flags && status.flags.admin_erp_enabled && account && account.role === "admin" && bridgeAvailable),
      "admin-retry": adminWriteEnabled,
      "admin-refund": adminWriteEnabled,
      "admin-freeze": adminWriteEnabled,
      "payment-create": Boolean(status.flags && status.flags.payment_enabled && bridgeAvailable),
      "feature-draft": Boolean(bridgeAvailable),
      "feature-estimate": Boolean(bridgeAvailable),
      "feature-confirm": webFeatureExecutionAvailable,
      "create-ticket": Boolean(bridgeAvailable)
    };
    merge({
      ...context,
      catalog,
      oauthProviders,
      telegramConnection,
      isAdmin: Boolean(account && account.role === "admin"),
      profile: account ? {
        displayName: accountDisplayName,
        email: account.email,
        accountType: account.account_type || "standard",
        locale: account.profile && account.profile.locale,
        timezone: account.profile && account.profile.timezone,
        avatarStyle: account.profile && account.profile.avatar_style,
        loginMethods: account.login_methods || {}
      } : {},
      linkStatus: { linked: telegramLinked },
      session: {
        authenticated: Boolean(account), csrfReady: Boolean(me.csrf_token), csrfToken: me.csrf_token || "",
        displayName: accountDisplayName, email: account ? account.email : ""
      },
      bridge: { available: bridgeAvailable, csrfReady: Boolean(me.csrf_token), configured: Boolean(status.bridge_configured), copyfastEnabled, featureExecutionAvailable: webFeatureExecutionAvailable, featureExecutionFeatures: webFeatureExecutionFeatures },
      assetVaultEnabled,
      projectPackageEnabled,
      documentOperationsEnabled,
      imageToPdfEnabled,
      pdfToWordEnabled,
      imageOperationsEnabled,
      imageResizeEnabled,
      // These owner-scoped reads start as loading on every signed hydration.
      // A native operation form may only become actionable after both the
      // Asset Vault source projection and its own history projection return.
      assetVaultReadState: account && assetVaultEnabled ? "loading" : "guarded",
      imageOperationsReadState: account && assetVaultEnabled && imageOperationsEnabled ? "loading" : "guarded",
      documentOperations: account && Array.isArray(context.documentOperations) ? context.documentOperations : [],
      imageOperations: account && Array.isArray(context.imageOperations) ? context.imageOperations : [],
      workspaceDraftFeatures: webWorkspaceDraftFeatures,
      pwaEnabled: Boolean(status.flags && status.flags.pwa_enabled),
      capabilities,
      pageStates: {
        ...featurePageStates(catalog, {}, webFeatureExecutionFeatures, webWorkspaceDraftFeatures, Boolean(account && me.csrf_token)),
        ...nativeDocumentPageStates,
        ...nativeImagePageStates
      }
    });
    if (status.flags && status.flags.pwa_enabled && "serviceWorker" in navigator) {
      navigator.serviceWorker.register("/static/portal/service-worker.js").catch(() => {});
    }
    const currentPath = (context.path || window.location.pathname).split("?")[0];
    if (account && ["/campaigns", "/calendar", "/approvals"].includes(currentPath)) await hydrateCampaignPlans();
    else if (account && campaignPlanIdFromPath(currentPath)) await hydrateCampaignPlanDetail(currentPath);
    if (account && ["/projects", "/project-packages", "/dashboard"].includes(currentPath)) await hydrateProjects();
    else if (account && projectIdFromPath(currentPath)) await hydrateProjectDetail(currentPath);
    if (account && projectPackageEnabled && currentPath === "/project-packages") await hydrateProjectPackages();
    else if (account && projectPackageEnabled && projectIdFromPath(currentPath)) await hydrateProjectPackages(projectIdFromPath(currentPath));
    else if (account && currentPath === "/project-packages") merge({ projectPackages: [], pageStates: { ...(base().pageStates || {}), "/project-packages": "guarded" } });
    if (account && assetVaultEnabled && ["/asset-vault", "/dashboard", "/documents/split", "/documents/merge", "/documents/compress", "/documents/image-to-pdf", "/documents/pdf-to-word", "/image/resize"].includes(currentPath)) await hydrateAssetVault();
    else if (account && ["/asset-vault", "/image/resize"].includes(currentPath)) merge({
      vaultItems: [],
      assetVaultReadState: "guarded",
      pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
    });
    if (account && assetVaultEnabled && documentOperationsEnabled && ["/documents/split", "/documents/merge", "/documents/compress", "/documents/image-to-pdf", "/documents/pdf-to-word"].includes(currentPath)) await hydrateDocumentOperations();
    else if (account && ["/documents/split", "/documents/merge", "/documents/compress", "/documents/image-to-pdf", "/documents/pdf-to-word"].includes(currentPath)) merge({ documentOperations: [], pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" } });
    if (account && assetVaultEnabled && imageOperationsEnabled && currentPath === "/image/resize") await hydrateImageOperations();
    else if (account && currentPath === "/image/resize") merge({
      imageOperations: [],
      imageOperationsReadState: "guarded",
      pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
    });
    if (account && currentPath === "/account/activity") await hydrateAccountActivity();
    // Dashboard is a real signed workspace now, so it may show the same
    // owner-scoped, Web-only draft library as `/workspace`. This never calls
    // the Bot bridge and cannot create a job, quote, payment or provider task.
    if (account && ["/workspace", "/dashboard"].includes(currentPath)) await hydrateWorkspaceDrafts();
    if (account && linkChallengeRoute()) {
      const linkStatus = await hydrateLinkStatus();
      if (!telegramLinked) await resumeTelegramLinkChallenge(linkStatus);
    }
    // A callback can complete while the customer is in Telegram. On a reload
    // we recover only the HttpOnly browser challenge status, never its opaque
    // code or a Telegram identity from localStorage.
    if (!account && loginChallengeRoute()) await resumeTelegramLoginChallenge();
    if (!account) scheduleTelegramLoginPolling();
    if (account && !telegramLinked) scheduleTelegramLinkPolling();
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
      return link;
    } catch (_) {
      // The onboarding shell stays usable and does not infer a link from a
      // failed status check.  A future refresh remains available.
      return null;
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

  async function hydrateCampaignPlans() {
    try {
      const result = await api("/campaigns");
      const items = result.data && Array.isArray(result.data.items) ? result.data.items : [];
      merge({ campaignPlans: items.slice(0, 100) });
    } catch (_) {
      // A failed read must not make a browser-side plan, calendar, approval
      // or publication state appear. The existing empty board remains honest.
    }
  }

  async function hydrateCampaignPlanDetail(path) {
    const planId = campaignPlanIdFromPath(path);
    if (!planId) return;
    try {
      const result = await api(`/campaigns/${encodeURIComponent(planId)}`);
      const item = result.data && result.data.item && typeof result.data.item === "object" ? result.data.item : null;
      if (!item || String(item.id || "") !== planId || !validCampaignPlanId(item.id)) throw new Error("campaign detail unavailable");
      merge({
        campaignPlanDetail: item,
        pageStates: { ...(base().pageStates || {}), [path]: result.status || "read_only" }
      });
    } catch (_) {
      // A missing or cross-account plan remains an honest empty detail page.
      // Do not fall back to the Bot campaign system or retain a different
      // plan from an earlier hydration in browser state.
      merge({ campaignPlanDetail: {}, pageStates: { ...(base().pageStates || {}), [path]: "guarded" } });
    }
  }

  async function hydrateProjects() {
    try {
      const result = await api("/projects");
      const items = result.data && Array.isArray(result.data.items)
        ? result.data.items.filter((item) => item && validProjectId(item.id)).slice(0, 100)
        : [];
      merge({
        projects: items,
        // The GET projection itself is read-only, but Project Center has
        // independently capability-gated CSRF writes. Keep the page ready
        // rather than presenting an editable Web Workspace as read-only.
        pageStates: { ...(base().pageStates || {}), "/projects": "ready" }
      });
    } catch (_) {
      // Do not retain a previous account's authoring workspace after a failed
      // signed read. Project Center has no Bot/bridge fallback by design.
      merge({ projects: [], pageStates: { ...(base().pageStates || {}), "/projects": "guarded" } });
    }
  }

  function imageResizePrivateReadPageState(assetState, operationState) {
    if (base().imageResizeEnabled !== true) return "guarded";
    if (assetState === "ready" && operationState === "ready") return "ready";
    if (assetState === "loading" || operationState === "loading") return "processing";
    return "guarded";
  }

  async function hydrateAssetVault() {
    try {
      const result = await api("/asset-vault");
      const items = result.data && Array.isArray(result.data.items)
        ? result.data.items.filter((item) => item && validVaultAssetId(item.id) && String(item.state || "") === "active").slice(0, 100)
        : [];
      merge({
        vaultItems: items,
        assetVaultReadState: "ready",
        pageStates: {
          ...(base().pageStates || {}),
          "/asset-vault": "ready",
          "/image/resize": imageResizePrivateReadPageState("ready", String(base().imageOperationsReadState || "loading"))
        }
      });
      return items;
    } catch (_) {
      // A failed private read must clear the previous account projection. The
      // UI never falls back to Bot assets or browser storage.
      merge({
        vaultItems: [],
        assetVaultReadState: "failed",
        pageStates: {
          ...(base().pageStates || {}),
          "/asset-vault": "guarded",
          "/image/resize": imageResizePrivateReadPageState("failed", String(base().imageOperationsReadState || "loading"))
        }
      });
      return [];
    }
  }

  function documentOperationKindForCurrentRoute() {
    const currentPath = String(base().path || window.location.pathname || "").split("?")[0];
    if (currentPath === "/documents/image-to-pdf") return "image_to_pdf";
    if (currentPath === "/documents/pdf-to-word") return "pdf_to_word_text";
    return "";
  }

  async function hydrateDocumentOperations() {
    const kind = documentOperationKindForCurrentRoute();
    try {
      const result = kind === "image_to_pdf"
        ? await api("/document-operations?kind=image_to_pdf&limit=100")
        : kind === "pdf_to_word_text"
        ? await api("/document-operations?kind=pdf_to_word_text&limit=100")
        : await api("/document-operations");
      const items = result.data && Array.isArray(result.data.items)
        ? result.data.items
          .filter((item) => item && validDocumentOperationId(item.id) && ["pdf_split", "pdf_merge", "pdf_optimize", "image_to_pdf", "pdf_to_word_text"].includes(String(item.kind || "")))
          .slice(0, 100)
        : [];
      merge({
        documentOperations: items,
        pageStates: {
          ...(base().pageStates || {}),
          "/documents/split": "ready",
          "/documents/merge": "ready",
          "/documents/compress": "ready",
          "/documents/image-to-pdf": base().imageToPdfEnabled === true ? "ready" : "guarded",
          "/documents/pdf-to-word": base().pdfToWordEnabled === true ? "ready" : "guarded"
        }
      });
      return items;
    } catch (_) {
      // Clear the projection on every failed signed read. A document artifact
      // is never substituted with a Bot asset, stale account data or a
      // browser-generated preview.
      merge({
        documentOperations: [],
        pageStates: {
          ...(base().pageStates || {}),
          "/documents/split": "guarded",
          "/documents/merge": "guarded",
          "/documents/compress": "guarded",
          "/documents/image-to-pdf": "guarded",
          "/documents/pdf-to-word": "guarded"
        }
      });
      return [];
    }
  }

  async function hydrateImageOperations() {
    try {
      const result = await api("/image-operations?kind=image_resize&limit=100");
      const items = result.data && Array.isArray(result.data.items)
        ? result.data.items
          .filter((item) => item && validImageOperationId(item.id) && String(item.kind || "") === "image_resize")
          .slice(0, 100)
        : [];
      merge({
        imageOperations: items,
        imageOperationsReadState: "ready",
        pageStates: {
          ...(base().pageStates || {}),
          "/image/resize": imageResizePrivateReadPageState(String(base().assetVaultReadState || "loading"), "ready")
        }
      });
      return items;
    } catch (_) {
      // Never substitute stale, Bot-owned or browser-generated output when a
      // private read fails. The server-side history remains the only source.
      merge({
        imageOperations: [],
        imageOperationsReadState: "failed",
        pageStates: {
          ...(base().pageStates || {}),
          "/image/resize": imageResizePrivateReadPageState(String(base().assetVaultReadState || "loading"), "failed")
        }
      });
      return [];
    }
  }

  async function hydrateProjectDetail(path) {
    const projectId = projectIdFromPath(path);
    if (!projectId) return;
    try {
      const result = await api(`/projects/${encodeURIComponent(projectId)}`);
      const project = result.data && result.data.project && typeof result.data.project === "object" ? result.data.project : null;
      const documents = result.data && Array.isArray(result.data.documents)
        ? result.data.documents.filter((item) => item && validProjectId(item.id)).slice(0, 100)
        : [];
      if (!project || String(project.id || "") !== projectId || !validProjectId(project.id)) throw new Error("project detail unavailable");
      merge({
        projectDetail: project,
        projectDocuments: documents,
        studioDocumentDetail: {},
        pageStates: { ...(base().pageStates || {}), [path]: "ready" }
      });
    } catch (_) {
      merge({ projectDetail: {}, projectDocuments: [], studioDocumentDetail: {}, pageStates: { ...(base().pageStates || {}), [path]: "guarded" } });
    }
  }

  async function hydrateProjectPackages(projectId) {
    const selectedProjectId = String(projectId || "").trim();
    if (selectedProjectId && !validProjectId(selectedProjectId)) return [];
    const path = selectedProjectId ? `/projects/${encodeURIComponent(selectedProjectId)}/packages` : "/project-packages";
    try {
      const result = await api(path);
      const items = result.data && Array.isArray(result.data.items)
        ? result.data.items.filter((item) => item && validProjectPackageId(item.id) && (!selectedProjectId || String(item.project_id || "") === selectedProjectId)).slice(0, 100)
        : [];
      const current = Array.isArray(base().projectPackages) ? base().projectPackages : [];
      const remaining = selectedProjectId
        ? current.filter((item) => !item || String(item.project_id || "") !== selectedProjectId)
        : [];
      merge({
        projectPackages: [...items, ...remaining].slice(0, 100),
        pageStates: { ...(base().pageStates || {}), [selectedProjectId ? `/projects/${selectedProjectId}` : "/project-packages"]: "ready" }
      });
      return items;
    } catch (_) {
      // A failed owner-scoped read must clear that projection. Never keep a
      // previous account's package metadata or fall back to Bot assets/jobs.
      const current = Array.isArray(base().projectPackages) ? base().projectPackages : [];
      const remaining = selectedProjectId ? current.filter((item) => !item || String(item.project_id || "") !== selectedProjectId) : [];
      merge({
        projectPackages: remaining,
        pageStates: { ...(base().pageStates || {}), [selectedProjectId ? `/projects/${selectedProjectId}` : "/project-packages"]: "guarded" }
      });
      return [];
    }
  }

  async function hydrateStudioDocument(documentId) {
    if (!validProjectId(documentId)) throw new Error("Mã Studio Document không hợp lệ.");
    const result = await api(`/projects/documents/${encodeURIComponent(documentId)}`);
    const document = result.data && result.data.document && typeof result.data.document === "object" ? result.data.document : null;
    if (!document || String(document.id || "") !== String(documentId) || !validProjectId(document.id)) throw new Error("Studio Document không còn khả dụng.");
    const versions = result.data && Array.isArray(result.data.versions) ? result.data.versions.slice(0, 50) : [];
    merge({ studioDocumentDetail: { document, versions } });
    return { document, versions };
  }

  async function hydrateAccountActivity() {
    try {
      const result = await api("/account/activity");
      const items = result.data && Array.isArray(result.data.items) ? result.data.items.slice(0, 50) : [];
      merge({
        accountActivity: items,
        pageStates: { ...(base().pageStates || {}), "/account/activity": result.status || "read_only" }
      });
    } catch (_) {
      // Do not retain another account's activity or invent browser history.
      // An empty history is the only safe fallback for a failed signed read.
      merge({ accountActivity: [], pageStates: { ...(base().pageStates || {}), "/account/activity": "guarded" } });
    }
  }

  async function hydrateWorkspaceDrafts() {
    try {
      const result = await api("/workspace/drafts?include_archived=true");
      const items = result.data && Array.isArray(result.data.items) ? result.data.items.filter((item) => item && validWorkspaceDraftId(item.id)).slice(0, 100) : [];
      merge({
        workspaceDrafts: items,
        pageStates: { ...(base().pageStates || {}), "/workspace": result.status || "read_only" }
      });
    } catch (_) {
      // Do not retain stale data from a different signed account or invent a
      // browser-owned library after a failed owner-scoped read.
      merge({ workspaceDrafts: [], pageStates: { ...(base().pageStates || {}), "/workspace": "guarded" } });
    }
  }

  async function hydrateCanonicalData() {
    const context = base();
    const path = (context.path || window.location.pathname).split("?")[0];
    try {
      if (path === "/dashboard") {
        const [wallet, jobs, assets, readiness, tickets] = await Promise.all([
          api("/wallet"), api("/jobs"), api("/assets"), api("/features/status"),
          // A read failure for the optional attention card must not hide the
          // rest of the signed dashboard or turn an unknown ticket state into
          // a browser-side alert.
          api("/support/tickets").catch(() => ({ data: { items: [] } }))
        ]);
        merge({
          wallet: wallet.data || null,
          jobs: jobs.data && jobs.data.items ? jobs.data.items : [],
          assets: assets.data && assets.data.items ? assets.data.items : [],
          tickets: tickets.data && tickets.data.items ? tickets.data.items : [],
          readiness: readiness.data || {},
          pageStates: { ...(base().pageStates || {}), ...featurePageStates(base().catalog || [], readiness.data || {}, base().bridge && base().bridge.featureExecutionFeatures), [path]: "read_only" }
        });
      } else if (path === "/pricing") {
        const pricing = await api("/pricing");
        merge({ pricingCatalog: pricing.data || {}, pageStates: { ...(base().pageStates || {}), [path]: "read_only" } });
      } else if (path === "/packages") {
        const packages = await api("/packages");
        merge({ packageCatalog: packages.data || {}, pageStates: { ...(base().pageStates || {}), [path]: "read_only" } });
      } else if (path === "/membership") {
        const [wallet, packages, readiness] = await Promise.all([api("/wallet"), api("/packages"), api("/features/status")]);
        merge({
          wallet: wallet.data || null,
          packageCatalog: packages.data || {},
          readiness: readiness.data || {},
          pageStates: { ...(base().pageStates || {}), ...featurePageStates(base().catalog || [], readiness.data || {}, base().bridge && base().bridge.featureExecutionFeatures), [path]: "read_only" }
        });
      } else if (path === "/wallet" || path === "/wallet/topup") {
        const [wallet, history, packages] = await Promise.all([api("/wallet"), api("/wallet/history"), api("/packages")]);
        merge({ wallet: wallet.data, walletHistory: history.data && history.data.items ? history.data.items : [], packageCatalog: packages.data || {}, pageStates: path === "/wallet" ? { ...(base().pageStates || {}), [path]: "read_only" } : (base().pageStates || {}) });
      } else if (path === "/jobs") {
        const jobs = await api("/jobs");
        const items = jobs.data && jobs.data.items ? jobs.data.items : [];
        merge({ jobs: items, pageStates: { ...(base().pageStates || {}), [path]: "read_only" } });
        scheduleJobPolling(path, items);
      } else if (path.startsWith("/jobs/")) {
        const jobId = jobIdFromPath(path);
        if (!jobId) return;
        const [job, assets] = await Promise.all([
          api(`/jobs/${encodeURIComponent(jobId)}`),
          api("/assets").catch(() => ({ data: { items: [] } }))
        ]);
        const record = exactJobRecord(job.data, jobId);
        merge({
          jobDetail: record,
          jobAssets: ownedAssetsForJob(record, assets.data && assets.data.items),
          pageStates: { ...(base().pageStates || {}), [path]: job.status || "read_only" }
        });
        scheduleJobPolling(path, record);
      } else if (path === "/voice/outputs") {
        const readiness = await api("/features/status");
        merge({
          readiness: readiness.data || {},
          pageStates: { ...(base().pageStates || {}), ...featurePageStates(base().catalog || [], readiness.data || {}, base().bridge && base().bridge.featureExecutionFeatures) }
        });
      } else if (path === "/assets" || ["/image/history", "/image/assets", "/video/preview", "/video/export", "/music/library", "/music-library", "/music/sfx-library", "/subtitle/formats"].includes(path)) {
        const assets = await api("/assets");
        merge({ assets: assets.data && assets.data.items ? assets.data.items : [], pageStates: { ...(base().pageStates || {}), [path]: "read_only" } });
      } else if (path === "/video/progress") {
        const jobs = await api("/jobs");
        const items = jobs.data && jobs.data.items ? jobs.data.items : [];
        merge({ jobs: items, pageStates: { ...(base().pageStates || {}), [path]: "read_only" } });
        scheduleJobPolling(path, items);
      } else if (path === "/image/resize") {
        // Native image operations hydrate separately from Asset Vault. Do not
        // request pricing/readiness from the bridge or overwrite the strict
        // server-side guarded/ready state with a generic image feature badge.
      } else if ((path === "/image" || (path.startsWith("/image/") && path !== "/image/history")) || (path === "/video" || (path.startsWith("/video/") && !["/video/progress", "/video/preview", "/video/export"].includes(path)))) {
        const [pricing, readiness] = await Promise.all([api("/pricing"), api("/features/status")]);
        merge({
          pricingCatalog: pricing.data || {},
          readiness: readiness.data || {},
          pageStates: featurePageStates(base().catalog || [], readiness.data || {}, base().bridge && base().bridge.featureExecutionFeatures)
        });
      } else if (path === "/tts" || path === "/dubbing" || path.startsWith("/voice")) {
        const [profiles, readiness] = await Promise.all([api("/voice/profiles"), api("/features/status")]);
        merge({
          voiceProfiles: profiles.data && profiles.data.items ? profiles.data.items : [],
          readiness: readiness.data || {},
          pageStates: featurePageStates(base().catalog || [], readiness.data || {}, base().bridge && base().bridge.featureExecutionFeatures)
        });
      } else if (path === "/tickets") {
        const tickets = await api("/support/tickets");
        merge({ tickets: tickets.data && tickets.data.items ? tickets.data.items : [], pageStates: { ...(base().pageStates || {}), [path]: "read_only" } });
      } else if (path.startsWith("/admin")) {
        const admin = await readAdminPath(path);
        merge({
          adminData: admin.data || {},
          pageStates: { ...(base().pageStates || {}), [path]: admin.status === "completed" ? "read_only" : (admin.status || "read_only") }
        });
      } else {
        const readiness = await api("/features/status");
        merge({ readiness: readiness.data || {}, pageStates: featurePageStates(base().catalog || [], readiness.data || {}, base().bridge && base().bridge.featureExecutionFeatures) });
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
    const replacingSource = replacingSingleImageSource(route, fields);
    const uploadIds = replacingSource ? [] : (Array.isArray(priorInput.upload_ids) ? priorInput.upload_ids.filter((item) => typeof item === "string" && item) : []);
    const priorUploads = replacingSource ? [] : (priorFlow && priorFlow.data && Array.isArray(priorFlow.data.uploads) ? priorFlow.data.uploads : []);
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

  async function refreshTelegramLoginChallenge({ silent = false } = {}) {
    let status;
    try {
      status = await api("/auth/telegram/login/status");
    } catch (error) {
      const failure = error && error.payload && typeof error.payload === "object" ? error.payload : {};
      const errorCode = String(failure.error_code || "");
      // These are expected terminal states for a one-time browser-bound
      // challenge. Preserve the public server message and stop polling rather
      // than turning an expired/rejected Bot proof into a noisy retry loop.
      if (["TELEGRAM_LOGIN_ACCOUNT_REQUIRED", "TELEGRAM_LOGIN_EXPIRED", "TELEGRAM_LOGIN_CHALLENGE_REQUIRED"].includes(errorCode)) {
        const terminalData = {
          ...(failure.data || {}),
          recovered: errorCode !== "TELEGRAM_LOGIN_CHALLENGE_REQUIRED",
          expired: errorCode === "TELEGRAM_LOGIN_EXPIRED"
        };
        // Do not retain an expired code/deep link in JavaScript state. A stale
        // one-time capability must never look usable after the server has
        // revoked it.
        merge({ telegramLoginFlow: { status: failure.status || "guarded", message: failure.message || "Telegram chưa liên kết với tài khoản Web.", errorCode, data: terminalData } });
        stopTelegramLoginPolling();
        if (!silent) toast(failure.message || "Telegram chưa liên kết với tài khoản Web.");
        return false;
      }
      throw error;
    }
    const previous = base().telegramLoginFlow && typeof base().telegramLoginFlow === "object" ? base().telegramLoginFlow : {};
    merge({ telegramLoginFlow: { ...previous, status: status.status || "awaiting_confirm", message: status.message, errorCode: status.error_code || "", data: { ...(previous.data || {}), ...(status.data || {}) } } });
    if (!(status.data && status.data.ready === true)) {
      if (!silent) toast(status.message);
      return false;
    }
    return completeTelegramLoginChallenge();
  }

  async function completeTelegramLoginChallenge() {
    // `complete` consumes only the browser-bound one-time challenge that this
    // page created. The Bot callback remains the identity proof; nothing in
    // this browser request contains a Telegram ID or Bot credential.
    stopTelegramLoginPolling();
    const completed = await api("/auth/telegram/login/complete", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    toast(completed.message);
    await hydrate();
    const requested = requestedPortalRoute();
    // A successful Web sign-in owns a full Web Workspace even when the
    // customer has not opted into Telegram. Linking remains an optional
    // companion connector and must never trap an email/OAuth user in
    // onboarding before they can open their own projects or studios.
    window.location.assign(requested || "/dashboard");
    return true;
  }

  async function resumeTelegramLoginChallenge() {
    // On reload, the code is purposefully absent from JavaScript memory, but
    // the short-lived HttpOnly browser challenge remains a safe capability to
    // ask whether the Bot callback has already completed.
    if (!loginChallengeRoute() || telegramLoginResumeProbeInFlight || telegramChallengePending(base().telegramLoginFlow)) return false;
    telegramLoginResumeProbeInFlight = true;
    try {
      const status = await api("/auth/telegram/login/status");
      const previous = base().telegramLoginFlow && typeof base().telegramLoginFlow === "object" ? base().telegramLoginFlow : {};
      merge({ telegramLoginFlow: { ...previous, status: status.status || "awaiting_confirm", message: status.message, errorCode: status.error_code || "", data: { ...(status.data || {}), recovered: true } } });
      if (status.data && status.data.ready === true) return completeTelegramLoginChallenge();
      scheduleTelegramLoginPolling();
      return false;
    } catch (error) {
      const failure = error && error.payload && typeof error.payload === "object" ? error.payload : {};
      const errorCode = String(failure.error_code || "");
      // A normal visitor has no login challenge; do not render an error. An
      // expiry is useful feedback because the user may have returned from the
      // Bot after the one-time window elapsed.
      if (errorCode === "TELEGRAM_LOGIN_CHALLENGE_REQUIRED") return false;
      if (errorCode === "TELEGRAM_LOGIN_EXPIRED") {
        merge({ telegramLoginFlow: { status: failure.status || "failed", message: failure.message || "Mã đăng nhập Telegram đã hết hạn. Hãy tạo mã mới.", errorCode, data: { recovered: true, expired: true } } });
        stopTelegramLoginPolling();
      }
      return false;
    } finally {
      telegramLoginResumeProbeInFlight = false;
    }
  }

  async function completeTelegramLinkChallenge() {
    stopTelegramLinkPolling();
    const completed = await api("/auth/telegram/link/complete", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    merge({ linkStatus: completed.data || { linked: true }, linkFlow: {} });
    toast(completed.message);
    await hydrate();
    const requested = requestedPortalRoute();
    toast(requested ? "Telegram đã được liên kết. Đang mở lại workflow bạn đã chọn." : "Telegram đã được liên kết. Đang mở Dashboard.");
    window.location.assign(requested || "/dashboard");
    return true;
  }

  function recoverTelegramLinkFlow(result) {
    const data = result && result.data && typeof result.data === "object" ? result.data : {};
    const previous = base().linkFlow && typeof base().linkFlow === "object" ? base().linkFlow : {};
    const previousData = previous.data && typeof previous.data === "object" ? previous.data : {};
    if (data.pending !== true && data.ready_to_complete !== true) return false;
    merge({
      linkStatus: data,
      linkFlow: {
        ...previous,
        status: result.status || "awaiting_confirm",
        message: result.message || "Đang chờ Bot xác minh Telegram.",
        errorCode: result.error_code || "",
        // A reload never restores the code. If it only existed in memory,
        // expose a safe recovered marker and let the user either wait for the
        // Bot callback or deliberately replace the pending code.
        data: { ...previousData, ...data, recovered: typeof previousData.code !== "string" || !previousData.code }
      }
    });
    return true;
  }

  async function refreshTelegramLinkChallenge({ silent = false } = {}) {
    const result = await api("/auth/telegram/link/status");
    merge({ linkStatus: result.data || {} });
    if (result.data && result.data.linked) {
      stopTelegramLinkPolling();
      await hydrate();
      const requested = requestedPortalRoute();
      toast(requested ? "Telegram đã được liên kết. Đang mở lại workflow bạn đã chọn." : "Telegram đã được liên kết. Đang mở Dashboard.");
      window.location.assign(requested || "/dashboard");
      return true;
    }
    if (result.data && result.data.ready_to_complete === true) {
      recoverTelegramLinkFlow(result);
      return completeTelegramLinkChallenge();
    }
    if (recoverTelegramLinkFlow(result)) {
      if (!silent) toast(result.message);
      return false;
    }
    const previous = base().linkFlow && typeof base().linkFlow === "object" ? base().linkFlow : {};
    const previousData = previous.data && typeof previous.data === "object" ? previous.data : {};
    if (typeof previousData.code === "string" || previousData.recovered === true) {
      merge({ linkFlow: { status: "failed", message: "Mã liên kết Telegram đã hết hạn hoặc không còn thuộc phiên Web này. Hãy tạo mã mới.", errorCode: "LINK_CODE_INVALID", data: { expired: true } } });
      stopTelegramLinkPolling();
    }
    if (!silent) toast(result.message);
    return false;
  }

  async function resumeTelegramLinkChallenge(statusResult) {
    // A reload deliberately does not restore the code/deep link. The signed
    // session can nevertheless ask the server whether that *same* browser
    // session still owns an active pending challenge.
    if (!linkChallengeRoute() || telegramLinkResumeProbeInFlight || telegramChallengePending(base().linkFlow)) return false;
    telegramLinkResumeProbeInFlight = true;
    try {
      const result = statusResult || await api("/auth/telegram/link/status");
      if (!result || !(result.data && typeof result.data === "object")) return false;
      if (result.data.linked === true) return true;
      if (result.data.ready_to_complete === true) {
        recoverTelegramLinkFlow(result);
        return completeTelegramLinkChallenge();
      }
      if (recoverTelegramLinkFlow(result)) {
        scheduleTelegramLinkPolling();
      }
      return false;
    } finally {
      telegramLinkResumeProbeInFlight = false;
    }
  }

  function scheduleTelegramLoginPolling(delayMs) {
    const flow = base().telegramLoginFlow;
    if (!loginChallengeRoute() || !portalIsVisible() || !telegramChallengePending(flow)) return;
    telegramLoginPollDeadline = telegramChallengeDeadline(flow, telegramLoginPollDeadline);
    if (Date.now() >= telegramLoginPollDeadline || telegramLoginPollTimer) return;
    const delay = Number.isFinite(Number(delayMs)) ? Math.max(0, Number(delayMs)) : TELEGRAM_CHALLENGE_POLL_INTERVAL_MS;
    telegramLoginPollTimer = window.setTimeout(async () => {
      telegramLoginPollTimer = 0;
      try {
        const completed = await refreshTelegramLoginChallenge({ silent: true });
        telegramLoginPollFailures = 0;
        if (!completed) scheduleTelegramLoginPolling();
      } catch (_) {
        telegramLoginPollFailures += 1;
        const retryDelay = Math.min(TELEGRAM_CHALLENGE_POLL_MAX_BACKOFF_MS, TELEGRAM_CHALLENGE_POLL_INTERVAL_MS * (2 ** Math.min(telegramLoginPollFailures, 2)));
        scheduleTelegramLoginPolling(retryDelay);
      }
    }, delay);
  }

  function scheduleTelegramLinkPolling(delayMs) {
    const flow = base().linkFlow;
    if (!linkChallengeRoute() || !portalIsVisible() || !telegramChallengePending(flow)) return;
    telegramLinkPollDeadline = telegramChallengeDeadline(flow, telegramLinkPollDeadline);
    if (Date.now() >= telegramLinkPollDeadline || telegramLinkPollTimer) return;
    const delay = Number.isFinite(Number(delayMs)) ? Math.max(0, Number(delayMs)) : TELEGRAM_CHALLENGE_POLL_INTERVAL_MS;
    telegramLinkPollTimer = window.setTimeout(async () => {
      telegramLinkPollTimer = 0;
      try {
        const completed = await refreshTelegramLinkChallenge({ silent: true });
        telegramLinkPollFailures = 0;
        if (!completed) scheduleTelegramLinkPolling();
      } catch (_) {
        telegramLinkPollFailures += 1;
        const retryDelay = Math.min(TELEGRAM_CHALLENGE_POLL_MAX_BACKOFF_MS, TELEGRAM_CHALLENGE_POLL_INTERVAL_MS * (2 ** Math.min(telegramLinkPollFailures, 2)));
        scheduleTelegramLinkPolling(retryDelay);
      }
    }, delay);
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
      if (action === "asset-vault-upload") {
        const file = fields.file;
        if (!file || typeof file !== "object" || typeof file.name !== "string" || !Number.isFinite(Number(file.size)) || Number(file.size) < 1) {
          throw new Error("Hãy chọn một tệp hợp lệ trước khi lưu vào Asset Vault.");
        }
        const displayName = String(fields.display_name || "").replace(/\s+/g, " ").trim();
        const projectId = String(fields.project_id || "").trim();
        if (displayName.length > 120) throw new Error("Tên hiển thị Asset Vault tối đa 120 ký tự.");
        if (projectId && !validProjectId(projectId)) throw new Error("Project đính kèm không hợp lệ.");
        const fingerprint = `${file.name}:${Number(file.size)}:${Number(file.lastModified || 0)}:${displayName}:${projectId}`;
        const submission = acquireSubmission("asset-vault:upload", fingerprint);
        if (!submission) {
          toast("Tệp đang được lưu. Vui lòng chờ phản hồi từ Asset Vault.", "error");
          return;
        }
        setActionBusy(action, route, true);
        try {
          const formData = new FormData();
          formData.append("file", file, file.name);
          if (displayName) formData.append("display_name", displayName);
          if (projectId) formData.append("project_id", projectId);
          const result = await api("/asset-vault/upload", {
            method: "POST",
            headers: { "Idempotency-Key": submission.key },
            // Do not set Content-Type: the browser owns the multipart
            // boundary, while api() still supplies the signed CSRF header.
            body: formData
          });
          const asset = result.data && result.data.asset && typeof result.data.asset === "object" ? result.data.asset : null;
          if (!asset || !validVaultAssetId(asset.id)) throw new Error("Asset Vault chưa trả metadata tệp hợp lệ.");
          merge({ vaultItems: [asset, ...(Array.isArray(base().vaultItems) ? base().vaultItems.filter((item) => !item || String(item.id || "") !== String(asset.id)) : [])].slice(0, 100) });
          await hydrateAssetVault();
          toast(result.message || "Đã lưu tệp vào Asset Vault.");
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "asset-vault-archive") {
        const assetId = String(detail.vaultAssetId || "").trim();
        if (!validVaultAssetId(assetId)) throw new Error("Mã Asset Vault không hợp lệ.");
        const submission = acquireSubmission(`asset-vault:${assetId}:archive`, "archive");
        if (!submission) {
          toast("Tệp đang được lưu trữ. Vui lòng chờ phản hồi từ Asset Vault.", "error");
          return;
        }
        setActionBusy(action, route, true);
        try {
          const result = await api(`/asset-vault/${encodeURIComponent(assetId)}/archive`, {
            method: "POST",
            headers: { "Idempotency-Key": submission.key }
          });
          await hydrateAssetVault();
          toast(result.message || "Đã lưu trữ tệp Asset Vault.");
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "asset-vault-refresh") {
        await hydrateAssetVault();
        toast("Đã làm mới Asset Vault.");
        return;
      }
      if (action === "document-operation-pdf-split") {
        const sourceAssetId = String(fields.source_asset_id || "").trim();
        const pageRange = String(fields.page_range || "").trim();
        if (!validVaultAssetId(sourceAssetId)) throw new Error("Hãy chọn một PDF riêng tư hợp lệ từ Asset Vault.");
        if (!/^\d+(?:-\d+)?$/.test(pageRange)) throw new Error("Khoảng trang phải là một trang hoặc dải liên tiếp, ví dụ 2 hoặc 2-5.");
        const scope = `document-operation:pdf-split:${sourceAssetId}`;
        const submission = acquireSubmission(scope, `${sourceAssetId}:${pageRange}`);
        if (!submission) {
          toast("PDF Split đang được máy chủ xử lý. Vui lòng chờ phản hồi.", "error");
          return;
        }
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api("/document-operations/pdf-split", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              source_asset_id: sourceAssetId,
              page_range: pageRange,
              idempotency_key: submission.key
            })
          });
          acknowledged = true;
          const operation = result.data && result.data.operation && typeof result.data.operation === "object" ? result.data.operation : null;
          if (!operation || !validDocumentOperationId(operation.id) || String(operation.kind || "") !== "pdf_split") {
            throw new Error("Máy chủ chưa trả metadata PDF Split hợp lệ.");
          }
          await hydrateDocumentOperations();
          await hydrateAssetVault();
          toast(result.message || "Đã tạo PDF riêng tư đã được xác minh.");
        } catch (error) {
          // If the server returned any envelope, the key is no longer
          // ambiguous. Refresh owner-scoped projections so a recorded failed
          // operation/source-unavailable state cannot be hidden by the UI.
          acknowledged = acknowledged || Boolean(error && Number.isInteger(error.status) && error.status > 0);
          if (acknowledged) {
            await Promise.all([hydrateDocumentOperations(), hydrateAssetVault()]);
          }
          throw error;
        } finally {
          releaseSubmission(submission);
          if (acknowledged) discardSubmission(scope, submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "document-operation-pdf-merge") {
        // Ordered slots are intentionally collected by position instead of
        // a multi-select. The array becomes part of the server fingerprint,
        // so PDF 1 → PDF 8 is explicit and replay-safe.
        const sourceAssetIds = Array.from({ length: 8 }, (_, index) => String(fields[`source_asset_id_${index + 1}`] || "").trim())
          .filter(Boolean);
        if (sourceAssetIds.length < 2) throw new Error("Hãy chọn ít nhất hai PDF riêng tư theo thứ tự muốn gộp.");
        if (new Set(sourceAssetIds).size !== sourceAssetIds.length) throw new Error("Mỗi PDF nguồn chỉ được chọn một lần trong cùng thao tác gộp.");
        if (!sourceAssetIds.every(validVaultAssetId)) throw new Error("Một hoặc nhiều PDF nguồn không hợp lệ.");
        const scope = `document-operation:pdf-merge:${sourceAssetIds.join(":")}`;
        const submission = acquireSubmission(scope, sourceAssetIds.join(":"));
        if (!submission) {
          toast("PDF Merge đang được máy chủ xử lý. Vui lòng chờ phản hồi.", "error");
          return;
        }
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api("/document-operations/pdf-merge", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source_asset_ids: sourceAssetIds, idempotency_key: submission.key })
          });
          acknowledged = true;
          const operation = result.data && result.data.operation && typeof result.data.operation === "object" ? result.data.operation : null;
          if (!operation || !validDocumentOperationId(operation.id) || String(operation.kind || "") !== "pdf_merge") {
            throw new Error("Máy chủ chưa trả metadata PDF Merge hợp lệ.");
          }
          await Promise.all([hydrateDocumentOperations(), hydrateAssetVault()]);
          toast(result.message || "Đã gộp và xác minh PDF riêng tư.");
        } catch (error) {
          // A server envelope may contain a failed operation or a source
          // marked unavailable. Refresh only the signed, owner-scoped view;
          // never substitute Bot assets or client-side output.
          acknowledged = acknowledged || Boolean(error && Number.isInteger(error.status) && error.status > 0);
          if (acknowledged) await Promise.all([hydrateDocumentOperations(), hydrateAssetVault()]);
          throw error;
        } finally {
          releaseSubmission(submission);
          if (acknowledged) discardSubmission(scope, submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "document-operation-pdf-optimize") {
        const sourceAssetId = String(fields.source_asset_id || "").trim();
        if (!validVaultAssetId(sourceAssetId)) throw new Error("Hãy chọn một PDF riêng tư hợp lệ từ Asset Vault.");
        const scope = `document-operation:pdf-optimize:${sourceAssetId}`;
        const submission = acquireSubmission(scope, sourceAssetId);
        if (!submission) {
          toast("PDF Optimize đang được máy chủ xử lý. Vui lòng chờ phản hồi.", "error");
          return;
        }
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api("/document-operations/pdf-optimize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source_asset_id: sourceAssetId, idempotency_key: submission.key })
          });
          acknowledged = true;
          const operation = result.data && result.data.operation && typeof result.data.operation === "object" ? result.data.operation : null;
          if (!operation || !validDocumentOperationId(operation.id) || String(operation.kind || "") !== "pdf_optimize") {
            throw new Error("Máy chủ chưa trả metadata PDF Optimize hợp lệ.");
          }
          await Promise.all([hydrateDocumentOperations(), hydrateAssetVault()]);
          toast(result.message || "Đã tối ưu và xác minh PDF riêng tư.");
        } catch (error) {
          // A guarded no-reduction response is a deliberate honest result,
          // not a missing client-side preview. Re-read only owner-scoped
          // operations and Vault state so the source always remains clear.
          acknowledged = acknowledged || Boolean(error && Number.isInteger(error.status) && error.status > 0);
          if (acknowledged) await Promise.all([hydrateDocumentOperations(), hydrateAssetVault()]);
          throw error;
        } finally {
          releaseSubmission(submission);
          if (acknowledged) discardSubmission(scope, submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "document-operation-pdf-to-word") {
        const sourceAssetId = String(fields.source_asset_id || "").trim();
        if (!validVaultAssetId(sourceAssetId)) throw new Error("Hãy chọn một PDF riêng tư hợp lệ từ Asset Vault.");
        const scope = `document-operation:pdf-to-word:${sourceAssetId}`;
        const submission = acquireSubmission(scope, sourceAssetId);
        if (!submission) {
          toast("PDF có text → Word đang được máy chủ xử lý. Vui lòng chờ phản hồi.", "error");
          return;
        }
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api("/document-operations/pdf-to-word", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source_asset_id: sourceAssetId, idempotency_key: submission.key })
          });
          acknowledged = true;
          const operation = result.data && result.data.operation && typeof result.data.operation === "object" ? result.data.operation : null;
          if (!operation || !validDocumentOperationId(operation.id) || String(operation.kind || "") !== "pdf_to_word_text") {
            throw new Error("Máy chủ chưa trả metadata PDF có text → Word hợp lệ.");
          }
          await Promise.all([hydrateDocumentOperations(), hydrateAssetVault()]);
          toast(result.message || "Đã trích xuất text thực và xác minh DOCX riêng tư.");
        } catch (error) {
          // An empty/scanned PDF is a deliberate guarded result. Re-read the
          // owner-scoped record so the UI never hides it behind a client-side
          // OCR or a fabricated DOCX preview.
          acknowledged = acknowledged || Boolean(error && Number.isInteger(error.status) && error.status > 0);
          if (acknowledged) await Promise.all([hydrateDocumentOperations(), hydrateAssetVault()]);
          throw error;
        } finally {
          releaseSubmission(submission);
          if (acknowledged) discardSubmission(scope, submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "document-operation-image-to-pdf") {
        // Ordered slots intentionally become the exact server fingerprint:
        // Ảnh 1 → Ảnh 8 is the resulting PDF page order, never a browser
        // multi-select approximation or raw file/path upload.
        const sourceAssetIds = Array.from({ length: 8 }, (_, index) => String(fields[`source_asset_id_${index + 1}`] || "").trim())
          .filter(Boolean);
        if (sourceAssetIds.length < 1) throw new Error("Hãy chọn ít nhất một ảnh riêng tư theo thứ tự muốn tạo PDF.");
        if (new Set(sourceAssetIds).size !== sourceAssetIds.length) throw new Error("Mỗi ảnh nguồn chỉ được chọn một lần trong cùng thao tác.");
        if (!sourceAssetIds.every(validVaultAssetId)) throw new Error("Một hoặc nhiều ảnh nguồn không hợp lệ.");
        const scope = `document-operation:image-to-pdf:${sourceAssetIds.join(":")}`;
        const submission = acquireSubmission(scope, sourceAssetIds.join(":"));
        if (!submission) {
          toast("Ảnh → PDF đang được máy chủ xử lý. Vui lòng chờ phản hồi.", "error");
          return;
        }
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api("/document-operations/image-to-pdf", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source_asset_ids: sourceAssetIds, idempotency_key: submission.key })
          });
          acknowledged = true;
          const operation = result.data && result.data.operation && typeof result.data.operation === "object" ? result.data.operation : null;
          if (!operation || !validDocumentOperationId(operation.id) || String(operation.kind || "") !== "image_to_pdf") {
            throw new Error("Máy chủ chưa trả metadata Ảnh → PDF hợp lệ.");
          }
          await Promise.all([hydrateDocumentOperations(), hydrateAssetVault()]);
          toast(result.message || "Đã tạo và xác minh PDF riêng tư từ ảnh.");
        } catch (error) {
          // If a source turns out malformed, animated or tampered, retain
          // only the server-recorded state; never manufacture a client PDF.
          acknowledged = acknowledged || Boolean(error && Number.isInteger(error.status) && error.status > 0);
          if (acknowledged) await Promise.all([hydrateDocumentOperations(), hydrateAssetVault()]);
          throw error;
        } finally {
          releaseSubmission(submission);
          if (acknowledged) discardSubmission(scope, submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "image-operation-resize") {
        const sourceAssetId = String(fields.source_asset_id || "").trim();
        const preset = String(fields.preset || "custom").trim();
        const fitMode = String(fields.fit_mode || "pad").trim();
        const widthText = String(fields.target_width || "").trim();
        const heightText = String(fields.target_height || "").trim();
        if (!validVaultAssetId(sourceAssetId)) throw new Error("Hãy chọn một ảnh private hợp lệ từ Asset Vault.");
        if (!["custom", "1:1", "9:16", "16:9", "4:5", "3:4", "4:3", "3:2", "2:3", "21:9"].includes(preset)) throw new Error("Canvas / tỷ lệ chưa hợp lệ.");
        if (!["crop", "pad", "blur"].includes(fitMode)) throw new Error("Cách đặt ảnh chưa hợp lệ.");
        const parseDimension = (value, label) => {
          if (!value) return null;
          if (!/^\d{1,4}$/.test(value)) throw new Error(`${label} phải là số nguyên từ 128 đến 4096 px.`);
          const parsed = Number(value);
          if (!Number.isInteger(parsed) || parsed < 128 || parsed > 4096) throw new Error(`${label} phải là số nguyên từ 128 đến 4096 px.`);
          return parsed;
        };
        // Pixel fields are meaningful only for Custom. A stale browser field
        // after switching to a preset must never manufacture a contradictory
        // request for the server to reject.
        const targetWidth = preset === "custom" ? parseDimension(widthText, "Chiều rộng") : null;
        const targetHeight = preset === "custom" ? parseDimension(heightText, "Chiều cao") : null;
        if (preset === "custom" && (targetWidth === null || targetHeight === null)) {
          throw new Error("Canvas Tùy chỉnh cần đủ chiều rộng và chiều cao.");
        }
        const scope = `image-operation:resize:${sourceAssetId}:${preset}:${targetWidth || ""}x${targetHeight || ""}:${fitMode}`;
        const submission = acquireSubmission(scope, sourceAssetId);
        if (!submission) {
          toast("Resize Studio đang được máy chủ xử lý. Vui lòng chờ phản hồi.", "error");
          return;
        }
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api("/image-operations/resize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              source_asset_id: sourceAssetId,
              preset,
              target_width: targetWidth,
              target_height: targetHeight,
              fit_mode: fitMode,
              idempotency_key: submission.key
            })
          });
          acknowledged = true;
          const operation = result.data && result.data.operation && typeof result.data.operation === "object" ? result.data.operation : null;
          if (!operation || !validImageOperationId(operation.id) || String(operation.kind || "") !== "image_resize") {
            throw new Error("Máy chủ chưa trả metadata Resize Studio hợp lệ.");
          }
          await Promise.all([hydrateImageOperations(), hydrateAssetVault()]);
          toast(result.message || "Đã resize và xác minh PNG riêng tư.");
        } catch (error) {
          // A rejected/corrupt/animated input has no browser-side fallback.
          // Re-read only the server-owned private state after acknowledgment.
          acknowledged = acknowledged || Boolean(error && Number.isInteger(error.status) && error.status > 0);
          if (acknowledged) await Promise.all([hydrateImageOperations(), hydrateAssetVault()]);
          throw error;
        } finally {
          releaseSubmission(submission);
          if (acknowledged) discardSubmission(scope, submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "image-operation-refresh") {
        await Promise.all([hydrateImageOperations(), hydrateAssetVault()]);
        toast("Đã làm mới Resize & Aspect Studio.");
        return;
      }
      if (action === "document-operation-refresh") {
        await Promise.all([hydrateDocumentOperations(), hydrateAssetVault()]);
        toast("Đã làm mới Document Operations.");
        return;
      }
      if (action === "project-package-export") {
        const projectId = String(detail.projectId || projectIdFromPath(route) || "").trim();
        if (!validProjectId(projectId)) throw new Error("Mã Project không hợp lệ.");
        // The current document revisions are part of the browser-side intent
        // fingerprint only. The server alone captures actual content and
        // asset references inside its owner-scoped transaction.
        const revisions = (Array.isArray(base().projectDocuments) ? base().projectDocuments : [])
          .filter((item) => item && typeof item === "object" && String(item.project_id || "") === projectId && validProjectId(item.id))
          .map((item) => `${String(item.id)}:${Number(item.revision || 0)}`)
          .sort();
        const scope = `project-package:${projectId}:export`;
        const submission = acquireSubmission(scope, revisions.join("|"));
        if (!submission) {
          toast("Project Package đang được xuất. Vui lòng chờ phản hồi từ máy chủ.", "error");
          return;
        }
        setActionBusy(action, route, true);
        try {
          const result = await api(`/projects/${encodeURIComponent(projectId)}/packages`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ idempotency_key: submission.key })
          });
          const item = result.data && result.data.package && typeof result.data.package === "object" ? result.data.package : null;
          if (!item || !validProjectPackageId(item.id)) throw new Error("Máy chủ chưa trả Project Package hợp lệ.");
          await hydrateProjectPackages(projectId);
          toast(result.message || "Đã tạo Project Package riêng tư.");
        } catch (error) {
          // The server acknowledged this failed package state, so a later
          // deliberate export must receive a new idempotency intent instead
          // of replaying the same failed artifact record forever.
          discardSubmission(scope, submission);
          throw error;
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "project-package-refresh") {
        const projectId = String(detail.projectId || projectIdFromPath(route) || "").trim();
        await hydrateProjectPackages(projectId || undefined);
        toast("Đã làm mới Project Packages.");
        return;
      }
      if (action === "project-create") {
        const payload = {
          title: String(fields.title || "").trim(),
          summary: String(fields.summary || "").trim(),
          objective: String(fields.objective || "").trim()
        };
        const submission = acquireSubmission("project:create", JSON.stringify(payload));
        if (!submission) {
          toast("Project đang được tạo. Vui lòng chờ phản hồi từ Web Workspace.", "error");
          return;
        }
        setActionBusy(action, route, true);
        try {
          const result = await api("/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...payload, idempotency_key: submission.key }) });
          const project = result.data && result.data.project && typeof result.data.project === "object" ? result.data.project : null;
          if (!project || !validProjectId(project.id)) throw new Error("Web Workspace chưa trả Project hợp lệ.");
          merge({ projects: [project, ...(Array.isArray(base().projects) ? base().projects.filter((item) => !item || String(item.id || "") !== String(project.id)) : [])].slice(0, 100) });
          toast(result.message || "Đã tạo Project trên Web.");
          window.location.assign(`/projects/${encodeURIComponent(project.id)}`);
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "projects-refresh") {
        await hydrateProjects();
        toast("Đã làm mới Project Center.");
        return;
      }
      if (action === "project-update") {
        const projectId = String(detail.projectId || projectIdFromPath(route) || "").trim();
        if (!validProjectId(projectId)) throw new Error("Mã Project không hợp lệ.");
        const payload = {
          title: String(fields.title || "").trim(), summary: String(fields.summary || "").trim(),
          objective: String(fields.objective || "").trim(), state: String(fields.state || "active").trim()
        };
        const submission = acquireSubmission(`project:${projectId}:update`, JSON.stringify(payload));
        if (!submission) return;
        setActionBusy(action, route, true);
        try {
          const result = await api(`/projects/${encodeURIComponent(projectId)}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...payload, idempotency_key: submission.key }) });
          if (result.data && result.data.project) merge({ projectDetail: result.data.project });
          toast(result.message || "Đã cập nhật Project trên Web.");
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "studio-document-create") {
        const projectId = String(detail.projectId || projectIdFromPath(route) || "").trim();
        if (!validProjectId(projectId)) throw new Error("Mã Project không hợp lệ.");
        const payload = { kind: String(fields.kind || "").trim(), title: String(fields.title || "").trim(), content: String(fields.content || "") };
        const submission = acquireSubmission(`project:${projectId}:document:create`, JSON.stringify(payload));
        if (!submission) return;
        setActionBusy(action, route, true);
        try {
          const result = await api(`/projects/${encodeURIComponent(projectId)}/documents`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...payload, idempotency_key: submission.key }) });
          const document = result.data && result.data.document && typeof result.data.document === "object" ? result.data.document : null;
          await hydrateProjectDetail(route);
          if (document && validProjectId(document.id)) await hydrateStudioDocument(document.id);
          toast(result.message || "Đã thêm Studio Document.");
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "studio-document-open") {
        const documentId = String(detail.studioDocumentId || "").trim();
        await hydrateStudioDocument(documentId);
        toast("Đã nạp Studio Document và version history.");
        return;
      }
      if (action === "studio-document-update") {
        const documentId = String(detail.studioDocumentId || "").trim();
        const expectedRevision = Number(detail.studioDocumentRevision || 0);
        if (!validProjectId(documentId) || !Number.isInteger(expectedRevision) || expectedRevision < 1) throw new Error("Phiên bản Studio Document không hợp lệ.");
        const payload = { title: String(fields.title || "").trim(), content: String(fields.content || ""), expected_revision: expectedRevision };
        const submission = acquireSubmission(`studio-document:${documentId}:update`, JSON.stringify(payload));
        if (!submission) return;
        setActionBusy(action, route, true);
        try {
          const result = await api(`/projects/documents/${encodeURIComponent(documentId)}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...payload, idempotency_key: submission.key }) });
          if (result.ok) {
            await hydrateProjectDetail(route);
            await hydrateStudioDocument(documentId);
          }
          toast(result.message || "Đã lưu Studio Document.");
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "studio-document-restore") {
        const documentId = String(detail.studioDocumentId || "").trim();
        const expectedRevision = Number(detail.studioDocumentRevision || 0);
        const sourceRevision = Number(detail.studioDocumentVersion || 0);
        if (!validProjectId(documentId) || !Number.isInteger(expectedRevision) || expectedRevision < 1 || !Number.isInteger(sourceRevision) || sourceRevision < 1) throw new Error("Phiên bản Studio Document không hợp lệ.");
        const payload = { expected_revision: expectedRevision };
        const submission = acquireSubmission(`studio-document:${documentId}:restore:${sourceRevision}`, JSON.stringify(payload));
        if (!submission) return;
        setActionBusy(action, route, true);
        try {
          const result = await api(`/projects/documents/${encodeURIComponent(documentId)}/restore/${encodeURIComponent(String(sourceRevision))}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...payload, idempotency_key: submission.key }) });
          if (result.ok) {
            await hydrateProjectDetail(route);
            await hydrateStudioDocument(documentId);
          }
          toast(result.message || "Đã khôi phục Studio Document.");
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "campaign-create") {
        const campaign = campaignCreatePayload(fields);
        const scope = "campaign-plan:create";
        const submission = acquireSubmission(scope, JSON.stringify(campaign));
        if (!submission) {
          toast("Kế hoạch đang được lưu. Vui lòng chờ phản hồi từ máy chủ.", "error");
          return;
        }
        setActionBusy(action, route, true);
        try {
          const result = await api("/campaigns", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...campaign, idempotency_key: submission.key })
          });
          mergeCampaignPlan(result.data && result.data.item);
          toast(result.message || "Đã lưu kế hoạch Web.");
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "campaign-update") {
        const planId = String(fields.plan_id || "").trim();
        if (!validCampaignPlanId(planId)) throw new Error("Mã kế hoạch không hợp lệ.");
        const campaign = campaignCreatePayload(fields);
        const scope = `campaign-plan:${planId}:edit`;
        const submission = acquireSubmission(scope, JSON.stringify(campaign));
        if (!submission) {
          toast("Kế hoạch đang được cập nhật. Vui lòng chờ phản hồi từ máy chủ.", "error");
          return;
        }
        setActionBusy(action, route, true);
        try {
          const result = await api(`/campaigns/${encodeURIComponent(planId)}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...campaign, idempotency_key: submission.key })
          });
          mergeCampaignPlan(result.data && result.data.item);
          toast(result.message || "Đã cập nhật kế hoạch Web.");
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "campaign-update-status") {
        const update = campaignStatusPayload(fields);
        const scope = `campaign-plan:${update.plan_id}:status`;
        const submission = acquireSubmission(scope, `${update.approval_status}:${update.review_note}`);
        if (!submission) {
          toast("Trạng thái kế hoạch đang được cập nhật. Vui lòng chờ phản hồi từ máy chủ.", "error");
          return;
        }
        setActionBusy(action, route, true);
        try {
          const result = await api(`/campaigns/${encodeURIComponent(update.plan_id)}/status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ approval_status: update.approval_status, review_note: update.review_note, idempotency_key: submission.key })
          });
          mergeCampaignPlan(result.data && result.data.item);
          toast(result.message || "Đã cập nhật kế hoạch Web.");
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "workspace-draft-save" || action === "workspace-draft-update") {
        const feature = workspaceDraftFeatureForRoute(route);
        if (!feature) throw new Error("Workflow này chưa có mapping an toàn để lưu bản nháp Web.");
        const input = workspaceDraftInput(fields);
        if (!Object.keys(input).length) throw new Error("Hãy nhập ít nhất một giá trị brief an toàn trước khi lưu bản nháp.");
        const updating = action === "workspace-draft-update";
        const draftId = String(detail.workspaceDraftId || "").trim();
        if (updating && !validWorkspaceDraftId(draftId)) throw new Error("Mã bản nháp cần cập nhật không hợp lệ.");
        const title = `Bản nháp · ${String(feature.title || feature.key || "Workflow").trim()}`.slice(0, 120);
        const scope = updating ? `workspace-draft:${draftId}:update` : `workspace-draft:${feature.key}:${route}:create`;
        const submission = acquireSubmission(scope, JSON.stringify(input));
        if (!submission) {
          toast(updating ? "Bản nháp đang được cập nhật. Vui lòng chờ phản hồi từ máy chủ." : "Bản nháp đang được lưu. Vui lòng chờ phản hồi từ máy chủ.", "error");
          return;
        }
        setActionBusy(action, route, true);
        try {
          const result = await api(updating ? `/workspace/drafts/${encodeURIComponent(draftId)}` : "/workspace/drafts", {
            method: updating ? "PATCH" : "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(updating
              ? { title, input, idempotency_key: submission.key }
              : { feature_key: feature.key, title, input, idempotency_key: submission.key })
          });
          mergeWorkspaceDraft(result.data && result.data.item);
          toast(result.message || (updating ? "Đã cập nhật bản nháp Web." : "Đã lưu bản nháp Web."));
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "workspace-draft-resume") {
        const draftId = String(detail.workspaceDraftId || "").trim();
        if (!validWorkspaceDraftId(draftId)) throw new Error("Mã bản nháp không hợp lệ.");
        const result = await api(`/workspace/drafts/${encodeURIComponent(draftId)}`);
        const item = result.data && result.data.item && typeof result.data.item === "object" ? result.data.item : null;
        const feature = item && workspaceDraftFeatureForRoute(item.route);
        if (!item || !feature || String(feature.key || "") !== String(item.feature_key || "")) throw new Error("Bản nháp không còn khớp workflow Web đã đăng ký.");
        const restored = window.TOANAASPortal && typeof window.TOANAASPortal.restoreWorkspaceDraft === "function"
          ? window.TOANAASPortal.restoreWorkspaceDraft(item.route, item.input, item.id)
          : false;
        if (!restored) throw new Error("Bản nháp không có trường an toàn để đưa trở lại form.");
        const summary = { ...item };
        delete summary.input;
        mergeWorkspaceDraft(summary);
        window.history.pushState({}, "", item.route);
        merge({ path: item.route, title: "TOAN AAS" });
        await hydrate();
        toast("Đã đưa brief Web trở lại form. Tệp, upload, quote và lựa chọn canonical cần được chọn/kiểm tra lại.");
        return;
      }
      if (action === "workspace-draft-archive") {
        const draftId = String(detail.workspaceDraftId || "").trim();
        if (!validWorkspaceDraftId(draftId)) throw new Error("Mã bản nháp không hợp lệ.");
        const scope = `workspace-draft:${draftId}:archive`;
        const submission = acquireSubmission(scope, "archive");
        if (!submission) {
          toast("Bản nháp đang được lưu trữ. Vui lòng chờ phản hồi từ máy chủ.", "error");
          return;
        }
        setActionBusy(action, route, true);
        try {
          const result = await api(`/workspace/drafts/${encodeURIComponent(draftId)}/archive`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ idempotency_key: submission.key })
          });
          mergeWorkspaceDraft(result.data && result.data.item);
          toast(result.message || "Đã lưu trữ bản nháp Web.");
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "workspace-drafts-refresh") {
        await hydrateWorkspaceDrafts();
        toast("Đã làm mới thư viện bản nháp Web.");
        return;
      }
      if (action === "auth-register") {
        if (fields.password !== fields.confirm_password) throw new Error("Xác nhận mật khẩu chưa khớp.");
        const result = await api("/auth/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: fields.email || "", password: fields.password || "", display_name: fields.name || "" }) });
        toast(result.message);
        // Registration deliberately does not start a signed session. Keeping
        // both new and existing email responses identical prevents account
        // enumeration; login is the single password flow that issues cookie
        // and CSRF credentials.
        window.location.assign("/login?registered=1");
        return;
      }
      if (action === "auth-login") {
        const result = await api("/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: fields.email || "", password: fields.password || "" }) });
        toast(result.message);
        await hydrate();
        const requested = requestedPortalRoute();
        window.location.assign(requested || "/dashboard");
        return;
      }
      if (action === "start-telegram-login") {
        const submission = acquireSubmission("telegram-login-start", "one-time-browser-challenge");
        if (!submission) {
          toast("Mã đăng nhập Telegram đang được tạo. Vui lòng chờ phản hồi.", "error");
          return;
        }
        setActionBusy(action, route, true);
        try {
          stopTelegramLoginPolling();
          const result = await api("/auth/telegram/login/start", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
          merge({ telegramLoginFlow: { status: result.status || "awaiting_confirm", message: result.message, errorCode: result.error_code || "", data: result.data || {} } });
          toast(result.message);
          scheduleTelegramLoginPolling();
        } finally {
          releaseSubmission(submission);
          discardSubmission("telegram-login-start", submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "refresh-telegram-login") {
        await refreshTelegramLoginChallenge();
        return;
      }
      if (["link-oauth-telegram", "link-oauth-google", "link-oauth-github", "link-oauth-apple"].includes(action)) {
        const provider = action.replace("link-oauth-", "");
        const result = await api(`/auth/oauth/${provider}/link/start`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
        const startPath = safeOAuthStartPath(result.data && result.data.start_path);
        if (!startPath) throw new Error("Máy chủ chưa cấp đường dẫn OAuth hợp lệ.");
        window.location.assign(startPath);
        return;
      }
      if (action === "update-profile") {
        const result = await api("/auth/profile", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            display_name: fields.display_name || "",
            locale: fields.locale || "vi",
            timezone: fields.timezone || "Asia/Ho_Chi_Minh"
          })
        });
        toast(result.message);
        await hydrate();
        return;
      }
      if (action === "upgrade-telegram-account") {
        if (fields.password !== fields.confirm_password) throw new Error("Xác nhận mật khẩu chưa khớp.");
        const submission = acquireSubmission("telegram-account-upgrade", String(fields.email || "").trim().toLowerCase());
        if (!submission) {
          toast("Đang nâng cấp phương thức đăng nhập. Vui lòng chờ phản hồi.", "error");
          return;
        }
        setActionBusy(action, route, true);
        try {
          const result = await api("/auth/telegram-account/upgrade", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: fields.email || "", password: fields.password || "" })
          });
          toast(result.message);
          await hydrate();
        } finally {
          releaseSubmission(submission);
          discardSubmission("telegram-account-upgrade", submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "auth-logout") {
        const result = await api("/auth/logout", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
        toast(result.message || "Đã đăng xuất.");
        window.location.assign("/login");
        return;
      }
      if (action === "start-telegram-link") {
        const submission = acquireSubmission("telegram-link-start", "one-time-account-link");
        if (!submission) {
          toast("Mã liên kết Telegram đang được tạo. Vui lòng chờ phản hồi.", "error");
          return;
        }
        setActionBusy(action, route, true);
        try {
          stopTelegramLinkPolling();
          const result = await api("/auth/telegram/link/start", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
          merge({ linkFlow: { status: result.status || "awaiting_confirm", message: result.message, data: result.data || {} }, linkStatus: { linked: false } });
          toast(result.message);
          scheduleTelegramLinkPolling();
        } finally {
          releaseSubmission(submission);
          discardSubmission("telegram-link-start", submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "refresh-link-status") {
        await refreshTelegramLinkChallenge();
        return;
      }
      if (action === "refresh-account-activity") {
        await hydrateAccountActivity();
        toast("Đã làm mới nhật ký hoạt động Web.");
        return;
      }
      if (action === "copy-payment-command") {
        const command = String(detail.copyText || "");
        await copyPaymentBotCommand(command);
        toast(`Đã sao chép ${command}. Hãy dán lệnh vào bot TOAN AAS đã liên kết.`);
        return;
      }
      if (action === "copy-telegram-link-command") {
        const command = String(detail.copyText || "");
        await copyTelegramLinkCommand(command);
        toast("Đã sao chép lệnh liên kết. Hãy dán lệnh vào Bot TOAN AAS rồi quay lại tab này.");
        return;
      }
      if (action === "copy-bot-companion-command") {
        const command = String(detail.copyText || "");
        await copyBotCompanionCommand(command);
        toast(`Đã sao chép ${command}. Hãy dán lệnh vào Bot TOAN AAS đã liên kết.`);
        return;
      }
      if (action === "copy-analytics-bot-command") {
        const command = await copyAnalyticsBotCommand(fields);
        toast(`Đã sao chép ${command}. Hãy dán lệnh vào Bot TOAN AAS để Bot tạo báo cáo canonical.`);
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
        const result = await readAdminPath(path);
        merge({ adminData: result.data || {} });
        toast(result.message || "Đã làm mới dữ liệu vận hành đã được role-check.");
        return;
      }
      if (action === "admin-retry" || action === "admin-refund") {
        const jobId = String(detail.adminJobId || "").trim();
        if (!validAdminJobId(jobId)) throw new Error("Mã job quản trị không hợp lệ.");
        const operation = action === "admin-retry" ? "retry" : "refund";
        const scope = `admin:${operation}:${jobId}`;
        const submission = acquireSubmission(scope, `${route}:${jobId}`);
        if (!submission) {
          toast("Thao tác quản trị này đang chờ phản hồi canonical.", "error");
          return;
        }
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api(`/admin/jobs/${encodeURIComponent(jobId)}/${operation}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ input: {}, idempotency_key: submission.key })
          });
          acknowledged = true;
          toast(result.message || "Core Bridge đã nhận thao tác quản trị.");
          try {
            const refreshed = await readAdminPath(route);
            merge({ adminData: refreshed.data || {} });
          } catch (_) {
            // A canonical write can become visible before its read projection
            // refreshes. Preserve its explicit success response in the toast.
          }
        } catch (error) {
          // A server response is no longer ambiguous, even if it rejected the
          // intent. Keep the key only for an interrupted/no-response retry.
          acknowledged = Boolean(error && Number.isInteger(error.status) && error.status > 0);
          throw error;
        } finally {
          releaseSubmission(submission);
          if (acknowledged) discardSubmission(scope, submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "admin-freeze") {
        const feature = String(fields.feature || detail.adminFeature || "").trim();
        const frozenValue = String(fields.frozen || detail.adminFrozen || "").trim().toLowerCase();
        const frozen = frozenValue === "true" ? true : frozenValue === "false" ? false : null;
        const note = String(fields.note || "").trim();
        if (!validAdminFeatureKey(feature)) throw new Error("Tính năng cần freeze không hợp lệ.");
        if (frozen === null) throw new Error("Hãy chọn trạng thái đóng băng hoặc mở lại.");
        if (note.length < 5 || note.length > 300) throw new Error("Ghi chú vận hành cần từ 5 đến 300 ký tự.");
        const scope = `admin:freeze:${feature}`;
        const submission = acquireSubmission(scope, `${frozen}:${note}`);
        if (!submission) {
          toast("Thay đổi feature đang chờ phản hồi canonical.", "error");
          return;
        }
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api(`/admin/features/${encodeURIComponent(feature)}/freeze`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ frozen, note, idempotency_key: submission.key })
          });
          acknowledged = true;
          toast(result.message || "Core Bridge đã nhận thay đổi feature.");
          try {
            const refreshed = await readAdminPath(route);
            merge({ adminData: refreshed.data || {} });
          } catch (_) {
            // The read adapter may lag an acknowledged write; do not turn that
            // into a false failure or invent a new state in the browser.
          }
        } catch (error) {
          acknowledged = Boolean(error && Number.isInteger(error.status) && error.status > 0);
          throw error;
        } finally {
          releaseSubmission(submission);
          if (acknowledged) discardSubmission(scope, submission);
          setActionBusy(action, route, false);
        }
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
      if (action === "refresh-wallet-after-bot") {
        const [wallet, history] = await Promise.all([api("/wallet"), api("/wallet/history")]);
        merge({
          wallet: wallet.data || null,
          walletHistory: history.data && Array.isArray(history.data.items) ? history.data.items : []
        });
        toast("Đã làm mới số dư và lịch sử Xu canonical từ Bot.");
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
        if (featurePhase === "confirm" && !featureExecutionAllowed(feature)) {
          throw new Error("Workflow này chưa có adapter tạo job canonical được phê duyệt. Web chỉ cho draft và estimate.");
        }
        const intakeError = validateFeatureIntake(feature, route, fields, featurePhase);
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
          if (!prior || prior.phase !== "estimate" || prior.status !== "awaiting_confirm" || !estimateCanAdvanceToConfirm(estimate) || prior.estimateFingerprint !== inputFingerprint || !validWebQuoteReceipt(prior.webQuoteReceipt)) {
            throw new Error("Thông tin đã thay đổi hoặc chưa có estimate canonical hợp lệ. Hãy ước tính lại trước khi xác nhận.");
          }
        }
        const priorReceipt = featurePhase === "confirm" ? String(priorFeatureFlow(route).webQuoteReceipt || "") : "";
        const result = await api(`/features/${encodeURIComponent(feature)}/${featurePhase}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ input: featureInput, idempotency_key: featureSubmission.key, web_quote_receipt: priorReceipt })
        });
        const estimateAvailable = featurePhase === "estimate" && estimateCanAdvanceToConfirm(result.data && result.data.estimate);
        const webQuoteReceipt = estimateAvailable && validWebQuoteReceipt(result.data && result.data.web_quote_receipt)
          ? String(result.data.web_quote_receipt) : "";
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
              estimateFingerprint: estimateAvailable ? inputFingerprint : "",
              webQuoteReceipt
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
              estimateFingerprint: previous.estimateFingerprint || "",
              webQuoteReceipt: previous.webQuoteReceipt || ""
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
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      hydrate().then(() => {
        scheduleTelegramLoginPolling();
        scheduleTelegramLinkPolling();
      }).catch(() => {});
    }
  });
  window.addEventListener("visibilitychange", () => {
    if (portalIsVisible()) {
      scheduleTelegramLoginPolling();
      scheduleTelegramLinkPolling();
    } else {
      // No browser-side state changes while the user is in Telegram; resume
      // only when this same signed tab becomes visible again.
      if (telegramLoginPollTimer) window.clearTimeout(telegramLoginPollTimer);
      if (telegramLinkPollTimer) window.clearTimeout(telegramLinkPollTimer);
      telegramLoginPollTimer = 0;
      telegramLinkPollTimer = 0;
    }
  });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startInitialHydration, { once: true });
  else startInitialHydration();
}());
