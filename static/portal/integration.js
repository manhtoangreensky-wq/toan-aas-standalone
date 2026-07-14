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
    "image_create", "image_upscale", "image_transform", "image_remove_background"
  ]);
  const TIERED_VIDEO_FEATURES = new Set([
    "video_single", "video_product", "video_trend", "video_text_to_video", "video_quick",
    "video_image_to_video", "video_multiscene", "video_long"
  ]);
  const SINGLE_IMAGE_SOURCE_FEATURES = new Set([
    "image_upscale", "image_transform", "image_remove_background"
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
  const SUPPORT_SECRET_PATTERN = /\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|token|client[ _-]?secret|secret(?:[ _-]?key)?|password|passphrase|authorization)\b\s*(?:[:=]|\bis\b)\s*(?:bearer\s+)?[A-Za-z0-9_./+=:-]{8,}|\bbearer\s+[A-Za-z0-9._~+/=-]{12,}|\b(?:otp|cvv|cvc|pin|mã\s*(?:xác\s*(?:minh|thực)|otp)|ma\s*(?:xac\s*(?:minh|thuc)|otp)|verification\s+(?:code|token)|one[ -]?time(?:\s+(?:pass(?:word|code)?|code))?)\b/i;
  const SUPPORT_KNOWN_SECRET_TOKEN_PATTERN = /(?<![A-Za-z0-9_])(?:(?:sk|pk|rk)[_-][A-Za-z0-9_-]{12,}|gh(?:p|o|u|s|r)_[A-Za-z0-9]{12,}|github_pat_[A-Za-z0-9_]{12,}|xox(?:b|p|a|r|s)-[A-Za-z0-9-]{12,}|AIza[0-9A-Za-z_-]{20,}|(?:AKIA|ASIA)[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})(?![A-Za-z0-9_])/i;
  const SUPPORT_CARD_CANDIDATE_PATTERN = /(?<![0-9A-Za-z])[0-9](?:[\s./-]*[0-9]){12,18}(?![0-9A-Za-z])/g;
  const SUPPORT_MANUAL_PAYMENT_PROOF_PATTERN = /\b(?:tx(?:id|n)?|transaction\s+(?:hash|id|reference|no\.?|number)|mã\s*(?:(?:giao\s*)?(?:dịch|gd)|tham\s*chiếu|thanh\s*toán)|ma\s*(?:(?:giao\s*)?(?:dich|gd)|tham\s*chieu|thanh\s*toan)|biên\s*lai|bien\s*lai|chứng\s*từ|chung\s*tu|bill|số\s*tài\s*khoản|so\s*tai\s*khoan|stk|tài\s*khoản\s*(?:ngân\s*hàng|bank)|tai\s*khoan\s*(?:ngan\s*hang|bank)|bank\s+account|account\s+(?:number|no|id)|qr\s*(?:code|thanh\s*toán|thanh\s*toan)?)\b/i;
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
    "/prompt-studio": "prompt_studio", "/content/caption": "caption",
    "/content/hashtag": "hashtag", "/content/hook": "hook", "/content/script": "script",
    "/content/storyboard": "storyboard", "/content/pack": "content_pack",
    "/image": "image_create", "/image/create": "image_create", "/image/resize": "image_resize", "/image/upscale": "image_upscale", "/image/transform": "image_transform", "/image/remove-background": "image_remove_background", "/image/history": "image_history",
    "/video": "video_single", "/video/create": "video_single", "/video/long": "video_long", "/video/image-to-video": "video_image_to_video",
    "/video/product": "video_product", "/video/trend": "video_trend", "/video/multiscene": "video_multiscene", "/video/text-to-video": "video_text_to_video", "/video/quick": "video_quick", "/video/progress": "video_progress", "/video/preview": "video_preview", "/video/export": "video_export", "/video/add-ons": "video_addons", "/video/mux": "video_mux",
    "/voice": "voice_vault", "/voice/create": "voice_tts", "/voice/tts": "voice_tts", "/voice/vault": "voice_saved_tts", "/voice/saved": "voice_saved_tts", "/voice/clone": "voice_clone", "/voice/preview": "voice_preview", "/voice/outputs": "voice_outputs",
    "/music": "music_background", "/music/library": "music_library", "/music/sfx-library": "sfx_library", "/music/ai": "music_background", "/music/create": "music_background", "/music/song": "music_song", "/music/sfx": "music_sfx", "/music/upload": "music_upload",
    "/subtitle": "subtitle_asr", "/subtitle/create": "subtitle_create", "/translate": "subtitle_translate", "/dubbing": "video_dub", "/asr": "asr", "/subtitle/formats": "subtitle_formats", "/documents": "documents", "/documents/pdf": "documents_pdf", "/documents/ocr": "documents_ocr", "/documents/merge": "documents_merge", "/documents/split": "documents_split", "/documents/compress": "documents_compress", "/documents/image-to-pdf": "documents_image_to_pdf", "/documents/pdf-to-images": "documents_pdf_to_images", "/documents/pdf-to-word": "documents_pdf_to_word", "/documents/translate": "documents_translate"
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

  function supportSensitiveContentKind(...values) {
    const text = values.map((value) => String(value || "")).join("\n");
    if (SUPPORT_MANUAL_PAYMENT_PROOF_PATTERN.test(text)) return "manual-payment";
    const candidates = text.match(SUPPORT_CARD_CANDIDATE_PATTERN) || [];
    if (SUPPORT_SECRET_PATTERN.test(text) || SUPPORT_KNOWN_SECRET_TOKEN_PATTERN.test(text) || candidates.length) return "secret-or-card";
    return "";
  }

  function validateSupportIntake(subject, detail) {
    const sensitiveKind = supportSensitiveContentKind(subject, detail);
    if (sensitiveKind === "manual-payment") {
      return "Nạp thủ công không nhận bill, TXID, số tài khoản hoặc QR trong Web App. Hãy mở Bot đã liên kết và dùng /thucong để đối soát an toàn.";
    }
    if (sensitiveKind) {
      return "Ticket không nhận API key, token, mật khẩu, OTP/CVV hoặc số thẻ. Hãy xóa dữ liệu nhạy cảm trước khi gửi.";
    }
    return "";
  }

  // The native Support Desk uses the same client-side sensitive-data preflight
  // as the legacy bridge ticket form, but it never redirects people into a
  // Bot flow.  The server repeats this validation authoritatively.
  function validateWebSupportText(...values) {
    const sensitiveKind = supportSensitiveContentKind(...values);
    if (sensitiveKind === "manual-payment") {
      return "Web Support Desk không nhận bill, TXID, số tài khoản hoặc QR thanh toán trong nội dung hỗ trợ.";
    }
    // Native Support Desk intentionally follows the stricter server contract:
    // reject any 13–19 digit card-shaped sequence, even when it does not pass
    // Luhn, so client/server messages do not diverge around sensitive input.
    if (sensitiveKind) {
      return "Web Support Desk không nhận API key, token, mật khẩu, OTP/CVV hoặc số thẻ.";
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
      if (["documents", "documents_pdf"].includes(feature)) return "Document Studio dùng workflow PDF Web-native riêng; hãy chọn công cụ trong /documents.";
      if (!fileCount) return "Workflow tài liệu cần tệp đã vào staging canonical.";
      const operationByFeature = {
        documents_ocr: String(scalarField(fields, route, "operation") || "ocr_image"),
        documents_merge: "merge_pdf", documents_split: "split_pdf", documents_compress: "compress_pdf", documents_translate: "translate_document"
      };
      const operation = operationByFeature[feature] || String(scalarField(fields, route, "operation") || "");
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

  // Keep the Web-native Support Desk helpers outside the job-polling region.
  // They never read a provider/job record and remain independently available
  // to a signed Web account without a Bot bridge.
  const SUPPORT_CASE_STATES = new Set(["new", "reviewing", "waiting_user", "waiting_provider", "refund_pending", "resolved", "closed"]);
  const SUPPORT_CASE_CATEGORIES = new Set([
    "payment_topup", "image_error", "video_error", "document_pdf", "package_combo", "refund", "feature_request",
    "lead_consulting", "general_support", "service_consulting", "premium_lead", "custom_bot_lead", "other"
  ]);
  const SUPPORT_CASE_PRIORITIES = new Set(["low", "normal", "high", "urgent"]);

  function validSupportCaseId(value) {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || "").trim());
  }

  function validSupportRevision(value) {
    const parsed = Number(value);
    return Number.isInteger(parsed) && parsed >= 1 && parsed <= 1000000 ? parsed : 0;
  }

  function supportCaseIdFromPath(path) {
    const match = /^\/tickets\/([^/]+)$/.exec(String(path || "").split("?")[0]);
    const id = match ? String(match[1] || "") : "";
    return validSupportCaseId(id) ? id : "";
  }

  function supportAdminCaseIdFromPath(path) {
    const match = /^\/admin\/support\/([^/]+)$/.exec(String(path || "").split("?")[0]);
    const id = match ? String(match[1] || "") : "";
    return validSupportCaseId(id) ? id : "";
  }

  function isNativeSupportPath(path) {
    const normalized = String(path || "").split("?")[0];
    return normalized === "/support" || normalized === "/tickets" || Boolean(supportCaseIdFromPath(normalized))
      || normalized === "/admin/support" || Boolean(supportAdminCaseIdFromPath(normalized));
  }

  function supportCaseFilterPayload(value) {
    const source = value && typeof value === "object" ? value : {};
    const state = String(source.state || "all").trim().toLowerCase();
    const category = String(source.category || "").trim().toLowerCase();
    const q = String(source.q || "").replace(/\s+/g, " ").trim();
    if (state !== "all" && !SUPPORT_CASE_STATES.has(state)) throw new Error("Bộ lọc trạng thái Support Desk không hợp lệ.");
    if (category && !SUPPORT_CASE_CATEGORIES.has(category)) throw new Error("Bộ lọc nhóm Support Desk không hợp lệ.");
    if (q.length > 80) throw new Error("Từ khóa Support Desk tối đa 80 ký tự.");
    return { state, category, q };
  }

  function supportCasesPath(filter, admin) {
    const query = new URLSearchParams({ limit: admin ? "50" : "30", state: filter.state || "all" });
    if (filter.category) query.set("category", filter.category);
    if (filter.q) query.set("q", filter.q);
    return `${admin ? "/support/admin/cases" : "/support/cases"}?${query.toString()}`;
  }

  function supportCreatePayload(fields) {
    const category = String(fields.category || "general_support").trim().toLowerCase();
    const priority = String(fields.priority || "normal").trim().toLowerCase();
    const subject = String(fields.subject || "").replace(/\s+/g, " ").trim();
    const detail = String(fields.detail || "").trim();
    if (!SUPPORT_CASE_CATEGORIES.has(category)) throw new Error("Hãy chọn nhóm yêu cầu hợp lệ.");
    if (!SUPPORT_CASE_PRIORITIES.has(priority)) throw new Error("Hãy chọn mức ưu tiên hợp lệ.");
    if (subject.length < 3 || subject.length > 180) throw new Error("Chủ đề cần từ 3 đến 180 ký tự.");
    if (detail.length < 3 || detail.length > 4000) throw new Error("Nội dung cần từ 3 đến 4.000 ký tự.");
    const safetyError = validateWebSupportText(subject, detail);
    if (safetyError) throw new Error(safetyError);
    return { category, priority, subject, detail };
  }

  function supportReplyPayload(fields) {
    const body = String(fields.body || "").trim();
    if (!body || body.length > 4000) throw new Error("Phản hồi cần từ 1 đến 4.000 ký tự.");
    const safetyError = validateWebSupportText(body);
    if (safetyError) throw new Error(safetyError);
    return { body };
  }

  function supportAdminReplyPayload(fields) {
    const reply = supportReplyPayload(fields);
    const visibility = String(fields.visibility || "public").trim().toLowerCase();
    const nextState = String(fields.next_state || "").trim().toLowerCase();
    if (!["public", "internal"].includes(visibility)) throw new Error("Phạm vi phản hồi Support Desk không hợp lệ.");
    if (nextState && !SUPPORT_CASE_STATES.has(nextState)) throw new Error("Trạng thái sau phản hồi không hợp lệ.");
    return { ...reply, visibility, next_state: nextState };
  }

  function supportAdminUpdatePayload(fields) {
    const state = String(fields.state || "").trim().toLowerCase();
    const priority = String(fields.priority || "").trim().toLowerCase();
    const operationNote = String(fields.operation_note || "").trim();
    if (!SUPPORT_CASE_STATES.has(state)) throw new Error("Trạng thái Support Desk không hợp lệ.");
    if (!SUPPORT_CASE_PRIORITIES.has(priority)) throw new Error("Ưu tiên Support Desk không hợp lệ.");
    if (operationNote.length < 3 || operationNote.length > 360) throw new Error("Lý do thao tác cần từ 3 đến 360 ký tự.");
    const safetyError = validateWebSupportText(operationNote);
    if (safetyError) throw new Error(safetyError);
    return { state, priority, operation_note: operationNote };
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

  function validMemoryId(value) {
    return validProjectId(value);
  }

  function validMemoryRevision(value) {
    const parsed = Number(value);
    return Number.isInteger(parsed) && parsed >= 1 && parsed <= 1000000 ? parsed : 0;
  }

  function memoryNoteFilterPayload(value) {
    const source = value && typeof value === "object" ? value : {};
    const q = String(source.q || "").replace(/\s+/g, " ").trim();
    const priority = String(source.priority || "").trim().toLowerCase();
    const state = String(source.state || "all").trim().toLowerCase();
    if (q.length > 80) throw new Error("Từ khóa tìm ghi chú tối đa 80 ký tự.");
    if (priority && !["low", "normal", "important", "urgent"].includes(priority)) throw new Error("Bộ lọc ưu tiên ghi chú không hợp lệ.");
    if (!["all", "active", "archived"].includes(state)) throw new Error("Bộ lọc trạng thái ghi chú không hợp lệ.");
    return { q, priority, state };
  }

  function memoryNoteListPath(filter) {
    const query = new URLSearchParams({ state: filter.state || "all", limit: "100" });
    if (filter.q) query.set("q", filter.q);
    if (filter.priority) query.set("priority", filter.priority);
    return `/memory/notes?${query.toString()}`;
  }

  function memoryTagsFromInput(value) {
    const tags = [];
    const seen = new Set();
    String(value || "").split(",").forEach((candidate) => {
      const tag = candidate.replace(/\s+/g, " ").trim();
      if (!tag) return;
      if (tag.length > 40) throw new Error("Mỗi tag tối đa 40 ký tự.");
      const key = tag.toLocaleLowerCase("vi-VN");
      if (!seen.has(key)) {
        seen.add(key);
        tags.push(tag);
      }
    });
    if (tags.length > 12) throw new Error("Tối đa 12 tags cho một ghi chú.");
    return tags;
  }

  function memoryNotePayload(fields) {
    const title = String(fields.title || "").replace(/\s+/g, " ").trim();
    const content = String(fields.content || "").trim();
    const category = String(fields.category || "").replace(/\s+/g, " ").trim();
    const priority = String(fields.priority || "normal").trim().toLowerCase();
    if (title.length < 3 || title.length > 160) throw new Error("Tiêu đề ghi chú cần từ 3 đến 160 ký tự.");
    if (!content || content.length > 12000) throw new Error("Nội dung ghi chú cần từ 1 đến 12.000 ký tự.");
    if (category.length > 80) throw new Error("Danh mục tối đa 80 ký tự.");
    if (!["low", "normal", "important", "urgent"].includes(priority)) throw new Error("Ưu tiên ghi chú không hợp lệ.");
    return { title, content, tags: memoryTagsFromInput(fields.tags), category, priority };
  }

  // Prompt Library is a private Web-native recipe store. These helpers keep
  // browser validation aligned with its narrow server contract and never
  // invoke a remote generation service, Bot bridge action, job, wallet mutation or
  // payment request.
  const PROMPT_LIBRARY_STATES = new Set(["active", "archived"]);
  const PROMPT_VARIABLE_NAME_PATTERN = /^[A-Za-z_][A-Za-z0-9_]{0,63}$/;
  const PROMPT_FORBIDDEN_VARIABLE_NAMES = new Set(["__proto__", "constructor", "prototype"]);
  const PROMPT_QUOTED_SECRET_PATTERN = /\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|token|client[ _-]?secret|aws[ _-]?secret[ _-]?access[ _-]?key|secret(?:[ _-]?(?:key|access[ _-]?key))?|password|passphrase|authorization)\b\s*(?:['"]\s*)?(?:[:=]|\bis\b)\s*(?:['"]\s*)?(?:(?:bearer|basic)\s+)?[A-Za-z0-9_./+=:-]{8,}/i;
  const PROMPT_PRIVATE_KEY_PATTERN = /-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----|-----BEGIN OPENSSH PRIVATE KEY-----|\bssh-(?:rsa|ed25519|ecdsa)\s+[A-Za-z0-9+/]{32,}/i;
  const PROMPT_UNSAFE_CONTROL_PATTERN = /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/;
  const PROMPT_LIBRARY_IMPORT_MAX_CHARS = 1400000;
  const PROMPT_IMPORT_KEYS = new Set([
    "title", "category", "product_context", "platform", "style", "language", "prompt_text", "negative_prompt",
    "variables", "tags", "source", "license_note", "quality_score", "state"
  ]);

  function validPromptTemplateId(value) {
    return validProjectId(value);
  }

  function validPromptTemplateRevision(value) {
    return validMemoryRevision(value);
  }

  function promptTemplateIdFromPath(path) {
    const match = /^\/prompt-library\/([^/]+)$/.exec(String(path || "").split("?")[0]);
    const id = match ? String(match[1] || "") : "";
    return validPromptTemplateId(id) ? id : "";
  }

  function promptLibrarySafetyError(...values) {
    const text = values.map((value) => String(value || "")).join("\n");
    if (PROMPT_UNSAFE_CONTROL_PATTERN.test(text)) return "Prompt Library không nhận ký tự điều khiển không an toàn.";
    const sensitiveKind = supportSensitiveContentKind(text);
    if (sensitiveKind === "manual-payment") return "Prompt Library không nhận bill, TXID, QR, số tài khoản hoặc chứng từ thanh toán.";
    if (sensitiveKind || PROMPT_QUOTED_SECRET_PATTERN.test(text) || PROMPT_PRIVATE_KEY_PATTERN.test(text)) return "Prompt Library không nhận API key, khóa riêng, token, mật khẩu, OTP/CVV hoặc số thẻ.";
    return "";
  }

  function promptLibrarySingleLine(value, label, minimum, maximum) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (text.length < minimum || text.length > maximum || text.includes("\u0000")) throw new Error(`${label} cần từ ${minimum} đến ${maximum} ký tự hợp lệ.`);
    return text;
  }

  function promptLibraryOptionalLine(value, label, maximum) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (text.length > maximum || text.includes("\u0000")) throw new Error(`${label} tối đa ${maximum} ký tự hợp lệ.`);
    return text;
  }

  function promptLibraryContent(value, label, minimum, maximum) {
    const text = String(value || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
    if (text.length < minimum || text.length > maximum || text.includes("\u0000")) throw new Error(`${label} cần từ ${minimum} đến ${maximum} ký tự hợp lệ.`);
    return text;
  }

  function promptLibraryList(value, label, maximumItems, maximumItemLength) {
    const candidates = Array.isArray(value) ? value : String(value || "").split(",");
    const items = [];
    const seen = new Set();
    candidates.forEach((candidate) => {
      const item = String(candidate || "").replace(/\s+/g, " ").trim();
      if (!item) return;
      if (item.length > maximumItemLength || item.includes("\u0000")) throw new Error(`${label} tối đa ${maximumItemLength} ký tự mỗi mục.`);
      const key = item.toLocaleLowerCase("vi-VN");
      if (!seen.has(key)) {
        seen.add(key);
        items.push(item);
      }
    });
    if (items.length > maximumItems) throw new Error(`Tối đa ${maximumItems} ${label.toLowerCase()} cho một template.`);
    return items;
  }

  function promptTemplateVariables(value) {
    const variables = promptLibraryList(value, "variables", 24, 64);
    variables.forEach((name) => {
      if (!PROMPT_VARIABLE_NAME_PATTERN.test(name)) throw new Error("Tên variable chỉ dùng chữ, số và gạch dưới; bắt đầu bằng chữ hoặc gạch dưới.");
      if (PROMPT_FORBIDDEN_VARIABLE_NAMES.has(name.toLowerCase())) throw new Error("Tên variable này được dành riêng và không thể dùng trong preview.");
    });
    return variables;
  }

  function promptTemplateTags(value) {
    return promptLibraryList(value, "tags", 16, 48);
  }

  function promptLibraryFilterPayload(value) {
    const source = value && typeof value === "object" ? value : {};
    const q = promptLibraryOptionalLine(source.q, "Từ khóa tìm kiếm", 100);
    const category = promptLibraryOptionalLine(source.category, "Danh mục", 100);
    const platform = promptLibraryOptionalLine(source.platform, "Nền tảng", 100);
    const productContext = promptLibraryOptionalLine(source.product_context, "Ngữ cảnh", 100);
    const tag = promptLibraryOptionalLine(source.tag, "Tag", 48);
    const state = String(source.state || "all").trim().toLowerCase();
    if (state !== "all" && !PROMPT_LIBRARY_STATES.has(state)) throw new Error("Bộ lọc trạng thái Prompt Library không hợp lệ.");
    const safetyError = promptLibrarySafetyError(q, category, platform, productContext, tag);
    if (safetyError) throw new Error(safetyError);
    return { q, category, platform, product_context: productContext, tag, state };
  }

  function promptLibraryListPath(filter) {
    const query = new URLSearchParams({ state: filter.state || "all", limit: "100" });
    ["q", "category", "platform", "product_context", "tag"].forEach((name) => {
      if (filter[name]) query.set(name, filter[name]);
    });
    return `/prompt-library/templates?${query.toString()}`;
  }

  function promptTemplatePayload(fields) {
    const title = promptLibrarySingleLine(fields.title, "Tên template", 3, 180);
    const category = promptLibraryOptionalLine(fields.category || "General", "Danh mục", 100) || "General";
    const productContext = promptLibraryOptionalLine(fields.product_context || "general", "Ngữ cảnh", 100) || "general";
    const platform = promptLibraryOptionalLine(fields.platform || "general", "Nền tảng", 100) || "general";
    const style = promptLibraryOptionalLine(fields.style, "Phong cách", 100);
    const language = promptLibraryOptionalLine(fields.language || "vi", "Ngôn ngữ", 100) || "vi";
    const promptText = promptLibraryContent(fields.prompt_text, "Prompt", 1, 16000);
    const negativePrompt = promptLibraryContent(fields.negative_prompt, "Negative prompt", 0, 8000);
    const source = promptLibrarySingleLine(fields.source || "Tự soạn", "Nguồn", 2, 600);
    const licenseNote = promptLibrarySingleLine(fields.license_note || "Tôi có quyền sử dụng nội dung này.", "Quyền sử dụng", 2, 600);
    const qualityScore = Number(fields.quality_score);
    if (!Number.isInteger(qualityScore) || qualityScore < 0 || qualityScore > 100) throw new Error("Mức hoàn thiện cần là số nguyên từ 0 đến 100.");
    const variables = promptTemplateVariables(fields.variables);
    const tags = promptTemplateTags(fields.tags);
    const safetyError = promptLibrarySafetyError(title, category, productContext, platform, style, language, promptText, negativePrompt, source, licenseNote, ...variables, ...tags);
    if (safetyError) throw new Error(safetyError);
    return {
      title, category, product_context: productContext, platform, style, language, prompt_text: promptText,
      negative_prompt: negativePrompt, variables, tags, source, license_note: licenseNote, quality_score: qualityScore
    };
  }

  function promptLibraryImportPayload(fields) {
    const raw = String(fields.templates_json || "").trim();
    if (raw.length < 2 || raw.length > PROMPT_LIBRARY_IMPORT_MAX_CHARS) throw new Error("JSON import cần từ 2 đến 1.400.000 ký tự.");
    let decoded;
    try { decoded = JSON.parse(raw); } catch (_) { throw new Error("JSON template không hợp lệ."); }
    const templates = Array.isArray(decoded) ? decoded : (decoded && typeof decoded === "object" && Array.isArray(decoded.templates) ? decoded.templates : null);
    if (!templates || templates.length < 1 || templates.length > 50) throw new Error("Import cần từ 1 đến 50 template JSON.");
    return {
      templates: templates.map((item) => {
        if (!item || typeof item !== "object" || Array.isArray(item)) throw new Error("Mỗi template import phải là JSON object.");
        const unknown = Object.keys(item).filter((key) => !PROMPT_IMPORT_KEYS.has(key));
        if (unknown.length) throw new Error("JSON import có trường không được chấp nhận.");
        const state = String(item.state || "active").trim().toLowerCase();
        if (!PROMPT_LIBRARY_STATES.has(state)) throw new Error("Trạng thái template import không hợp lệ.");
        return { ...promptTemplatePayload(item), state };
      })
    };
  }

  // Audio Library & Briefing stays outside FEATURE_BY_PATH and the generic
  // Bot draft/estimate/confirm flow.  Its payloads describe only Web-owned
  // collection metadata and already-owned Asset Vault references; there is
  // deliberately no URL, external engine handle, Telegram file ID, job, wallet or payment
  // field anywhere in this client contract.
  const MEDIA_PROMPT_MODES = new Set(["background", "lyrics", "script", "melody", "custom"]);
  const MEDIA_COLLECTION_STATES = new Set(["active", "archived"]);
  const MEDIA_ITEM_ROLES = new Set(["music", "sfx", "reference"]);

  function validMediaCollectionId(value) {
    return validProjectId(value);
  }

  function validMediaRevision(value) {
    return validMemoryRevision(value);
  }

  function mediaWorkspaceCollectionIdFromPath(path) {
    const match = /^\/media-workspace\/([^/]+)$/.exec(String(path || "").split("?")[0]);
    const id = match ? String(match[1] || "") : "";
    return validMediaCollectionId(id) ? id : "";
  }

  function isNativeMediaWorkspacePath(path) {
    const normalized = String(path || "").split("?")[0];
    return normalized === "/media-workspace" || normalized === "/media-workspace/new" || Boolean(mediaWorkspaceCollectionIdFromPath(normalized));
  }

  function mediaWorkspaceSafetyError(...values) {
    const text = values.map((value) => String(value || "")).join("\n");
    if (PROMPT_UNSAFE_CONTROL_PATTERN.test(text)) return "Audio Library không nhận ký tự điều khiển không an toàn.";
    const sensitiveKind = supportSensitiveContentKind(text);
    if (sensitiveKind === "manual-payment") return "Audio Library không nhận bill, TXID, QR, số tài khoản hoặc chứng từ thanh toán.";
    if (sensitiveKind || PROMPT_QUOTED_SECRET_PATTERN.test(text) || PROMPT_PRIVATE_KEY_PATTERN.test(text)) return "Audio Library không nhận API key, khóa riêng, token, mật khẩu, OTP/CVV hoặc số thẻ.";
    return "";
  }

  function mediaWorkspaceLine(value, label, minimum, maximum, allowEmpty) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (text.length > maximum || (!allowEmpty && text.length < minimum) || text.includes("\u0000")) throw new Error(`${label} cần từ ${minimum} đến ${maximum} ký tự hợp lệ.`);
    return text;
  }

  function mediaWorkspaceContent(value, label, maximum) {
    const text = String(value || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
    if (text.length > maximum || text.includes("\u0000")) throw new Error(`${label} tối đa ${maximum.toLocaleString("vi-VN")} ký tự hợp lệ.`);
    return text;
  }

  function mediaWorkspaceTags(value, label) {
    const raw = Array.isArray(value) ? value : String(value || "").split(",");
    const values = [];
    const seen = new Set();
    raw.forEach((candidate) => {
      if (!String(candidate || "").trim()) return;
      const tag = mediaWorkspaceLine(candidate, label || "Tag", 1, 48, false);
      const key = tag.toLocaleLowerCase("vi-VN");
      if (!seen.has(key)) {
        seen.add(key);
        values.push(tag);
      }
    });
    if (values.length > 16) throw new Error("Tối đa 16 tags cho mỗi collection hoặc audio reference.");
    return values;
  }

  function mediaWorkspaceFilterPayload(value) {
    const source = value && typeof value === "object" ? value : {};
    const q = mediaWorkspaceLine(source.q, "Từ khóa tìm kiếm", 0, 100, true);
    const tag = mediaWorkspaceLine(source.tag, "Tag", 0, 48, true);
    const promptMode = mediaWorkspaceLine(source.prompt_mode, "Loại brief", 0, 24, true).toLowerCase();
    const state = String(source.state || "all").trim().toLowerCase();
    if (promptMode && !MEDIA_PROMPT_MODES.has(promptMode)) throw new Error("Bộ lọc loại brief không hợp lệ.");
    if (state !== "all" && !MEDIA_COLLECTION_STATES.has(state)) throw new Error("Bộ lọc trạng thái collection không hợp lệ.");
    const safety = mediaWorkspaceSafetyError(q, tag, promptMode, state);
    if (safety) throw new Error(safety);
    return { q, tag, prompt_mode: promptMode, state };
  }

  function mediaWorkspaceListPath(filter) {
    const query = new URLSearchParams({ state: filter.state || "all", limit: "100" });
    ["q", "tag", "prompt_mode"].forEach((name) => { if (filter[name]) query.set(name, filter[name]); });
    return `/media-workspace/collections?${query.toString()}`;
  }

  function mediaCollectionPayload(fields) {
    const title = mediaWorkspaceLine(fields.title, "Tên collection", 3, 180, false);
    const description = mediaWorkspaceContent(fields.description, "Mô tả", 6000);
    const creativeBrief = mediaWorkspaceContent(fields.creative_brief, "Music brief", 6000);
    const promptMode = mediaWorkspaceLine(fields.prompt_mode || "background", "Loại brief", 3, 24, false).toLowerCase();
    const useContext = mediaWorkspaceLine(fields.use_context || "general", "Ngữ cảnh sử dụng", 0, 160, true) || "general";
    const rightsNote = mediaWorkspaceLine(fields.rights_note || "", "Quyền sử dụng", 2, 800, false);
    const projectId = String(fields.project_id || "").trim();
    if (!MEDIA_PROMPT_MODES.has(promptMode)) throw new Error("Loại brief không hợp lệ.");
    if (projectId && !validProjectId(projectId)) throw new Error("Project liên kết không hợp lệ.");
    const tags = mediaWorkspaceTags(fields.tags, "Tag");
    const safety = mediaWorkspaceSafetyError(title, description, creativeBrief, promptMode, useContext, rightsNote, ...tags);
    if (safety) throw new Error(safety);
    return { title, description, creative_brief: creativeBrief, prompt_mode: promptMode, use_context: useContext, tags, rights_note: rightsNote, project_id: projectId };
  }

  function mediaItemPayload(fields, includeAsset) {
    const role = mediaWorkspaceLine(fields.role || "music", "Vai trò audio", 3, 24, false).toLowerCase();
    const titleOverride = mediaWorkspaceLine(fields.title_override, "Tên hiển thị", 0, 180, true);
    const attribution = mediaWorkspaceLine(fields.attribution, "Attribution", 0, 500, true);
    const licenseNote = mediaWorkspaceLine(fields.license_note || "", "Ghi chú license", 2, 800, false);
    const rawDuration = String(fields.user_declared_duration_seconds || "").trim();
    const duration = rawDuration === "" ? null : Number(rawDuration);
    if (!MEDIA_ITEM_ROLES.has(role)) throw new Error("Vai trò audio không hợp lệ.");
    if (duration !== null && (!Number.isInteger(duration) || duration < 1 || duration > 7200)) throw new Error("Thời lượng tự khai báo phải là số nguyên từ 1 đến 7.200 giây.");
    const tags = mediaWorkspaceTags(fields.tags, "Tag audio");
    const safety = mediaWorkspaceSafetyError(titleOverride, attribution, licenseNote, ...tags);
    if (safety) throw new Error(safety);
    const payload = { role, title_override: titleOverride, attribution, license_note: licenseNote, tags, favorite: fields.favorite === true, user_declared_duration_seconds: duration };
    if (includeAsset) {
      const assetId = String(fields.asset_id || "").trim();
      if (!validVaultAssetId(assetId)) throw new Error("Hãy chọn một audio Asset Vault hợp lệ.");
      payload.asset_id = assetId;
    }
    return payload;
  }

  // Creative Content Studio is a strict Web-native authoring boundary. It
  // never passes free text to generic feature execution, Bot bridge, provider,
  // payment or browser storage. These client checks mirror, but never replace,
  // server-side Pydantic, CSRF, owner and revision validation.
  const CONTENT_STUDIO_KINDS = new Set(["caption_hashtag", "content_ideas", "hook_script", "content_pack", "storyboard"]);
  const CONTENT_STUDIO_VARIANT_KINDS = new Set(["caption", "hashtag_set", "hook", "script", "storyboard", "content_pack", "content_ideas", "custom"]);
  const CONTENT_STUDIO_STATES = new Set(["active", "archived"]);

  function validContentBriefId(value) { return validProjectId(value); }
  function validContentStudioRevision(value) { return validMemoryRevision(value); }
  function contentBriefIdFromPath(path) {
    const match = /^\/content-studio\/([^/]+)$/.exec(String(path || "").split("?")[0]);
    const id = match ? String(match[1] || "") : "";
    return validContentBriefId(id) ? id : "";
  }
  function isNativeContentStudioPath(path) {
    const normalized = String(path || "").split("?")[0];
    return normalized === "/content-studio" || normalized === "/content-studio/new" || Boolean(contentBriefIdFromPath(normalized));
  }
  function contentStudioSafetyError(...values) {
    const text = values.map((value) => String(value || "")).join("\n");
    if (PROMPT_UNSAFE_CONTROL_PATTERN.test(text)) return "Content Studio không nhận ký tự điều khiển không an toàn.";
    const sensitiveKind = supportSensitiveContentKind(text);
    if (sensitiveKind === "manual-payment") return "Content Studio không nhận bill, TXID, QR, số tài khoản hoặc chứng từ thanh toán.";
    if (sensitiveKind || PROMPT_QUOTED_SECRET_PATTERN.test(text) || PROMPT_PRIVATE_KEY_PATTERN.test(text)) return "Content Studio không nhận API key, khóa riêng, token, mật khẩu, OTP/CVV hoặc số thẻ.";
    return "";
  }
  function contentStudioLine(value, label, minimum, maximum, allowEmpty) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (text.length > maximum || (!allowEmpty && text.length < minimum) || text.includes("\u0000")) throw new Error(label + " cần từ " + minimum + " đến " + maximum + " ký tự hợp lệ.");
    return text;
  }
  function contentStudioBody(value, label, maximum, allowEmpty) {
    const text = String(value || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
    if (text.length > maximum || (!allowEmpty && !text) || text.includes("\u0000")) throw new Error(label + " tối đa " + maximum.toLocaleString("vi-VN") + " ký tự hợp lệ.");
    return text;
  }
  function contentStudioTags(value) {
    const raw = Array.isArray(value) ? value : String(value || "").split(",");
    const result = [];
    const seen = new Set();
    raw.forEach((candidate) => {
      if (!String(candidate || "").trim()) return;
      const tag = contentStudioLine(candidate, "Tag", 1, 48, false);
      const fingerprint = tag.toLocaleLowerCase("vi-VN");
      if (!seen.has(fingerprint)) { seen.add(fingerprint); result.push(tag); }
    });
    if (result.length > 20) throw new Error("Tối đa 20 tags cho mỗi content brief hoặc content piece.");
    return result;
  }
  function contentStudioReference(value, label) {
    const id = String(value || "").trim();
    if (id && !validContentBriefId(id)) throw new Error(label + " không hợp lệ.");
    return id;
  }
  function contentBriefPayload(fields) {
    const title = contentStudioLine(fields.title, "Tên brief", 2, 180, false);
    const contentKind = contentStudioLine(fields.content_kind, "Loại nội dung", 1, 32, false).toLowerCase();
    const subject = contentStudioLine(fields.subject, "Chủ đề", 2, 700, false);
    const objective = contentStudioLine(fields.objective, "Mục tiêu", 0, 500, true);
    const audience = contentStudioLine(fields.audience, "Đối tượng", 0, 500, true);
    const platform = contentStudioLine(fields.platform, "Nền tảng", 0, 100, true);
    const tone = contentStudioLine(fields.tone, "Giọng điệu", 0, 160, true);
    const language = contentStudioLine(fields.language || "vi", "Ngôn ngữ", 1, 100, false);
    const callToAction = contentStudioBody(fields.call_to_action, "CTA", 600, true);
    const briefText = contentStudioBody(fields.brief_text, "Nội dung brief", 12000, false);
    const constraints = contentStudioBody(fields.constraints, "Ràng buộc", 6000, true);
    const rightsNote = contentStudioBody(fields.rights_note, "Ghi chú quyền sử dụng", 1000, true);
    const tags = contentStudioTags(fields.tags);
    if (!CONTENT_STUDIO_KINDS.has(contentKind)) throw new Error("Loại Content Studio không hợp lệ.");
    const values = [title, contentKind, subject, objective, audience, platform, tone, language, callToAction, briefText, constraints, rightsNote, ...tags];
    const safety = contentStudioSafetyError(...values);
    if (safety) throw new Error(safety);
    return {
      title, content_kind: contentKind, subject, objective, audience, platform, tone, language,
      call_to_action: callToAction, brief_text: briefText, constraints, tags, rights_note: rightsNote,
      project_id: contentStudioReference(fields.project_id, "Project liên kết"),
      campaign_plan_id: contentStudioReference(fields.campaign_plan_id, "Campaign liên kết"),
      prompt_template_id: contentStudioReference(fields.prompt_template_id, "Prompt template liên kết"),
      media_collection_id: contentStudioReference(fields.media_collection_id, "Audio collection liên kết")
    };
  }
  function contentVariantPayload(fields) {
    const kind = contentStudioLine(fields.kind || "custom", "Loại content piece", 1, 32, false).toLowerCase();
    const title = contentStudioLine(fields.title, "Tiêu đề content piece", 2, 180, false);
    const contentText = contentStudioBody(fields.content_text, "Nội dung content piece", 20000, false);
    const note = contentStudioBody(fields.note, "Ghi chú content piece", 2000, true);
    const tags = contentStudioTags(fields.tags);
    if (!CONTENT_STUDIO_VARIANT_KINDS.has(kind)) throw new Error("Loại content piece không hợp lệ.");
    const safety = contentStudioSafetyError(kind, title, contentText, note, ...tags);
    if (safety) throw new Error(safety);
    return { kind, title, content_text: contentText, note, tags };
  }
  function contentStudioFilterPayload(value) {
    const source = value && typeof value === "object" ? value : {};
    const q = contentStudioLine(source.q, "Từ khóa tìm kiếm", 0, 100, true);
    const tag = contentStudioLine(source.tag, "Tag", 0, 48, true);
    const kind = contentStudioLine(source.content_kind, "Loại nội dung", 0, 32, true).toLowerCase();
    const state = String(source.state || "all").trim().toLowerCase();
    if (kind && !CONTENT_STUDIO_KINDS.has(kind)) throw new Error("Bộ lọc loại Content Studio không hợp lệ.");
    if (state !== "all" && !CONTENT_STUDIO_STATES.has(state)) throw new Error("Bộ lọc trạng thái Content Studio không hợp lệ.");
    const safety = contentStudioSafetyError(q, tag, kind, state);
    if (safety) throw new Error(safety);
    return { q, tag, content_kind: kind, state };
  }
  function contentStudioListPath(filter) {
    const query = new URLSearchParams({ state: filter.state || "all", limit: "100" });
    ["q", "tag", "content_kind"].forEach((key) => { if (filter[key]) query.set(key, filter[key]); });
    return "/content-studio/briefs?" + query.toString();
  }

  // Voice Studio is deliberately a separate Web-native authoring boundary.
  // It never creates or transports audio, provider voice identifiers, Bot
  // profile identifiers, previews, jobs, payment intent or clone requests.
  // These narrow browser checks are defence in depth; the API remains the
  // authority for session, CSRF, ownership, consent, revision and storage.
  const VOICE_STUDIO_VAULT_KINDS = new Set(["delivery_style", "brand_narration", "consented_reference"]);
  const VOICE_STUDIO_SCRIPT_KINDS = new Set(["narration", "ad", "explainer", "podcast", "training", "custom"]);
  const VOICE_STUDIO_STATES = new Set(["active", "archived"]);
  const VOICE_STUDIO_CONSENT_STATUSES = new Set(["not_required", "self_attested", "revoked"]);
  const VOICE_STUDIO_IMITATION_PATTERN = /(?:clone\s+(?:giọng|voice)|clone\s*voice|nhái\s+giọng|bắt\s+chước\s+giọng|giống\s+(?:giọng|ca\s*sĩ|nghệ\s*sĩ)|giọng\s+của|voice\s+clone|imitate\s+voice|impersonate|sound(?:s)?\s+like|in\s+the\s+voice\s+of|voice\s+of|celebrity\s+voice|artist\s+voice|same\s+voice)/i;

  function validVoiceStudioVaultId(value) { return validProjectId(value); }
  function validVoiceStudioScriptId(value) { return validProjectId(value); }
  function validVoiceStudioRevision(value) { return validMemoryRevision(value); }
  function voiceVaultIdFromPath(path) {
    const match = /^\/voice-studio\/([^/]+)$/.exec(String(path || "").split("?")[0]);
    const id = match ? String(match[1] || "") : "";
    return validVoiceStudioVaultId(id) ? id : "";
  }
  function isNativeVoiceStudioPath(path) {
    const normalized = String(path || "").split("?")[0];
    return normalized === "/voice-studio" || normalized === "/voice-studio/new" || Boolean(voiceVaultIdFromPath(normalized));
  }
  function voiceStudioSafetyError(...values) {
    const text = values.map((value) => String(value || "")).join("\n");
    if (PROMPT_UNSAFE_CONTROL_PATTERN.test(text)) return "Voice Studio không nhận ký tự điều khiển không an toàn.";
    const sensitiveKind = supportSensitiveContentKind(text);
    if (sensitiveKind === "manual-payment") return "Voice Studio không nhận bill, TXID, QR, số tài khoản hoặc chứng từ thanh toán.";
    if (sensitiveKind || PROMPT_QUOTED_SECRET_PATTERN.test(text) || PROMPT_PRIVATE_KEY_PATTERN.test(text)) return "Voice Studio không nhận API key, khóa riêng, token, mật khẩu, OTP/CVV hoặc số thẻ.";
    if (VOICE_STUDIO_IMITATION_PATTERN.test(text)) return "Voice Studio không nhận chỉ dẫn mô phỏng, nhái hoặc clone giọng của một người cụ thể.";
    return "";
  }
  function voiceStudioLine(value, label, minimum, maximum, allowEmpty) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (text.length > maximum || (!allowEmpty && text.length < minimum) || text.includes("\u0000")) throw new Error(label + " cần từ " + minimum + " đến " + maximum + " ký tự hợp lệ.");
    return text;
  }
  function voiceStudioBody(value, label, maximum, allowEmpty) {
    const text = String(value || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
    if (text.length > maximum || (!allowEmpty && !text) || text.includes("\u0000")) throw new Error(label + " tối đa " + maximum.toLocaleString("vi-VN") + " ký tự hợp lệ.");
    return text;
  }
  function voiceStudioTags(value) {
    const raw = Array.isArray(value) ? value : String(value || "").split(",");
    const result = [];
    const seen = new Set();
    raw.forEach((candidate) => {
      if (!String(candidate || "").trim()) return;
      const tag = voiceStudioLine(candidate, "Tag", 1, 48, false);
      const fingerprint = tag.toLocaleLowerCase("vi-VN");
      if (!seen.has(fingerprint)) { seen.add(fingerprint); result.push(tag); }
    });
    if (result.length > 20) throw new Error("Tối đa 20 tags cho mỗi Voice Vault hoặc script.");
    return result;
  }
  function voiceStudioReference(value, label) {
    const id = String(value || "").trim();
    if (id && !validVoiceStudioVaultId(id)) throw new Error(label + " không hợp lệ.");
    return id;
  }
  function voiceVaultPayload(fields) {
    const title = voiceStudioLine(fields.title, "Tên voice direction", 2, 180, false);
    const vaultKind = voiceStudioLine(fields.vault_kind || "delivery_style", "Loại voice direction", 1, 32, false).toLowerCase();
    const language = voiceStudioLine(fields.language || "vi", "Ngôn ngữ", 1, 100, false);
    const styleNotes = voiceStudioBody(fields.style_notes, "Mô tả cách thể hiện", 1600, true);
    const useContext = voiceStudioBody(fields.use_context, "Ngữ cảnh sử dụng", 1600, true);
    const consentStatus = voiceStudioLine(fields.consent_status || "not_required", "Trạng thái consent", 1, 32, false).toLowerCase();
    const consentNote = voiceStudioBody(fields.consent_note, "Ghi chú consent", 1400, true);
    const tags = voiceStudioTags(fields.tags);
    if (!VOICE_STUDIO_VAULT_KINDS.has(vaultKind)) throw new Error("Loại Voice Vault không hợp lệ.");
    if (!VOICE_STUDIO_CONSENT_STATUSES.has(consentStatus)) throw new Error("Trạng thái consent không hợp lệ.");
    const isDefault = fields.is_default === true;
    if (vaultKind === "consented_reference") {
      if (!new Set(["self_attested", "revoked"]).has(consentStatus) || consentNote.length < 12) throw new Error("Reference cần self-attestation hoặc trạng thái đã thu hồi, cùng ghi chú tối thiểu 12 ký tự.");
      if (consentStatus === "revoked" && isDefault) throw new Error("Reference đã thu hồi consent không thể đặt làm direction mặc định local.");
    } else if (consentStatus !== "not_required") {
      throw new Error("Chỉ consented reference mới được gắn consent trong Voice Studio.");
    }
    const safety = voiceStudioSafetyError(title, vaultKind, language, styleNotes, useContext, consentStatus, consentNote, ...tags);
    if (safety) throw new Error(safety);
    return {
      title, vault_kind: vaultKind, language, style_notes: styleNotes, use_context: useContext,
      consent_status: consentStatus, consent_note: consentNote,
      is_default: isDefault,
      tags,
      project_id: voiceStudioReference(fields.project_id, "Project liên kết") || null,
      content_brief_id: voiceStudioReference(fields.content_brief_id, "Content Brief liên kết") || null
    };
  }
  function voiceScriptPayload(fields) {
    const title = voiceStudioLine(fields.title, "Tên script", 2, 180, false);
    const scriptKind = voiceStudioLine(fields.script_kind || "narration", "Loại script", 1, 32, false).toLowerCase();
    const language = voiceStudioLine(fields.language || "vi", "Ngôn ngữ", 1, 100, false);
    const audience = voiceStudioLine(fields.audience, "Đối tượng", 0, 500, true);
    const paceWpm = Number(fields.pace_wpm || 145);
    const scriptText = voiceStudioBody(fields.script_text, "Lời thoại", 24000, false);
    const deliveryNotes = voiceStudioBody(fields.delivery_notes, "Chỉ dẫn thể hiện", 5000, true);
    const pronunciationNotes = voiceStudioBody(fields.pronunciation_notes, "Ghi chú phát âm", 3000, true);
    const tags = voiceStudioTags(fields.tags);
    if (!VOICE_STUDIO_SCRIPT_KINDS.has(scriptKind)) throw new Error("Loại script Voice Studio không hợp lệ.");
    if (!Number.isInteger(paceWpm) || paceWpm < 80 || paceWpm > 240) throw new Error("Nhịp đọc cần là số nguyên từ 80 đến 240 WPM.");
    const safety = voiceStudioSafetyError(title, scriptKind, language, audience, scriptText, deliveryNotes, pronunciationNotes, ...tags);
    if (safety) throw new Error(safety);
    return {
      title, script_kind: scriptKind, language, audience, pace_wpm: paceWpm,
      script_text: scriptText, delivery_notes: deliveryNotes, pronunciation_notes: pronunciationNotes, tags
    };
  }
  function voiceStudioFilterPayload(value) {
    const source = value && typeof value === "object" ? value : {};
    const q = voiceStudioLine(source.q, "Từ khóa tìm kiếm", 0, 100, true);
    const tag = voiceStudioLine(source.tag, "Tag", 0, 48, true);
    const state = String(source.state || "all").trim().toLowerCase();
    if (state !== "all" && !VOICE_STUDIO_STATES.has(state)) throw new Error("Bộ lọc trạng thái Voice Studio không hợp lệ.");
    const safety = voiceStudioSafetyError(q, tag, state);
    if (safety) throw new Error(safety);
    return { q, tag, state };
  }
  function voiceStudioVaultListPath(filter) {
    const query = new URLSearchParams({ state: filter.state || "all", limit: "100" });
    ["q", "tag"].forEach((key) => { if (filter[key]) query.set(key, filter[key]); });
    return "/voice-studio/vaults?" + query.toString();
  }

  // Video Production Studio is an independent Web-native planning boundary.
  // It accepts structured editorial metadata only: it never accepts media
  // uploads, source URLs, renderer options or a request to manufacture a
  // result from the browser.
  const VIDEO_STUDIO_FORMATS = new Set(["short_form", "product_demo", "explainer", "ugc", "campaign", "custom"]);
  const VIDEO_STUDIO_ASPECT_RATIOS = new Set(["9:16", "16:9", "1:1", "4:5", "custom"]);
  const VIDEO_STUDIO_SCENE_TYPES = new Set(["hook", "problem", "solution", "product", "proof", "cta", "transition", "custom"]);
  const VIDEO_STUDIO_PLAN_STATES = new Set(["draft", "review", "approved", "archived"]);

  function validVideoStudioPlanId(value) { return validProjectId(value); }
  function validVideoStudioSceneId(value) { return validProjectId(value); }
  function validVideoStudioRevision(value) { return validMemoryRevision(value); }
  function videoPlanIdFromPath(path) {
    const match = /^\/video-studio\/([^/]+)$/.exec(String(path || "").split("?")[0]);
    const id = match ? String(match[1] || "") : "";
    return validVideoStudioPlanId(id) ? id : "";
  }
  function isNativeVideoStudioPath(path) {
    const normalized = String(path || "").split("?")[0];
    return normalized === "/video-studio" || normalized === "/video-studio/new" || Boolean(videoPlanIdFromPath(normalized));
  }
  function videoStudioSafetyError(...values) {
    const text = values.map((value) => String(value || "")).join("\n");
    if (PROMPT_UNSAFE_CONTROL_PATTERN.test(text)) return "Video Production Studio không nhận ký tự điều khiển không an toàn.";
    const sensitiveKind = supportSensitiveContentKind(text);
    if (sensitiveKind === "manual-payment") return "Video Production Studio không nhận bill, TXID, QR, số tài khoản hoặc chứng từ thanh toán.";
    if (sensitiveKind || PROMPT_QUOTED_SECRET_PATTERN.test(text) || PROMPT_PRIVATE_KEY_PATTERN.test(text)) return "Video Production Studio không nhận API key, khóa riêng, token, mật khẩu, OTP/CVV hoặc số thẻ.";
    if (/(?:file|javascript|data):|https?:\/\/|\bwww\./i.test(text)) return "Video Production Studio không nhận URL hoặc scheme tệp trong nội dung plan.";
    if (/\b(?:(?:provider|render|job|media)[ _-]*(?:id|ref(?:erence)?|token)|telegram[ _-]*file[ _-]*id|file[ _-]*id)\b\s*(?::|=|\bis\b)\s*\S+/i.test(text)) return "Video Production Studio không nhận provider, Bot, job hoặc media ID trong nội dung plan.";
    return "";
  }
  function videoStudioLine(value, label, minimum, maximum, allowEmpty) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (text.length > maximum || (!allowEmpty && text.length < minimum) || text.includes("\u0000")) throw new Error(label + " cần từ " + minimum + " đến " + maximum + " ký tự hợp lệ.");
    return text;
  }
  function videoStudioBody(value, label, maximum, allowEmpty) {
    const text = String(value || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
    if (text.length > maximum || (!allowEmpty && !text) || text.includes("\u0000")) throw new Error(label + " tối đa " + maximum.toLocaleString("vi-VN") + " ký tự hợp lệ.");
    return text;
  }
  function videoStudioTags(value) {
    const raw = Array.isArray(value) ? value : String(value || "").split(",");
    const result = [];
    const seen = new Set();
    raw.forEach((candidate) => {
      if (!String(candidate || "").trim()) return;
      const tag = videoStudioLine(candidate, "Tag", 1, 48, false);
      const fingerprint = tag.toLocaleLowerCase("vi-VN");
      if (!seen.has(fingerprint)) { seen.add(fingerprint); result.push(tag); }
    });
    if (result.length > 20) throw new Error("Tối đa 20 tags cho mỗi video plan hoặc scene.");
    return result;
  }
  function videoStudioReference(value, label) {
    const id = String(value || "").trim();
    if (id && !validVideoStudioPlanId(id)) throw new Error(label + " không hợp lệ.");
    return id;
  }
  function videoPlanPayload(fields) {
    const title = videoStudioLine(fields.title, "Tên video plan", 2, 180, false);
    const format = videoStudioLine(fields.format || "short_form", "Loại kế hoạch", 1, 32, false).toLowerCase();
    const language = videoStudioLine(fields.language || "vi", "Ngôn ngữ", 1, 100, false);
    const aspectRatio = videoStudioLine(fields.aspect_ratio || "9:16", "Tỷ lệ khung hình", 1, 32, false);
    const duration = Number(fields.target_duration_seconds);
    const objective = videoStudioBody(fields.objective, "Mục tiêu", 1200, true);
    const audience = videoStudioBody(fields.audience, "Đối tượng", 1200, true);
    const brief = videoStudioBody(fields.brief, "Creative brief", 12000, false);
    const tags = videoStudioTags(fields.tags);
    if (!VIDEO_STUDIO_FORMATS.has(format)) throw new Error("Loại video plan không hợp lệ.");
    if (!VIDEO_STUDIO_ASPECT_RATIOS.has(aspectRatio)) throw new Error("Tỷ lệ khung hình không hợp lệ.");
    if (!Number.isInteger(duration) || duration < 1 || duration > 7200) throw new Error("Thời lượng mục tiêu cần là số nguyên từ 1 đến 7.200 giây.");
    const safety = videoStudioSafetyError(title, format, language, aspectRatio, objective, audience, brief, ...tags);
    if (safety) throw new Error(safety);
    return {
      title, format, language, aspect_ratio: aspectRatio, target_duration_seconds: duration,
      objective, audience, brief, tags, project_id: videoStudioReference(fields.project_id, "Project liên kết") || null
    };
  }
  function videoScenePayload(fields) {
    const title = videoStudioLine(fields.title, "Tên scene", 2, 180, false);
    const sceneType = videoStudioLine(fields.scene_type || "custom", "Vai trò scene", 1, 32, false).toLowerCase();
    const duration = Number(fields.duration_seconds);
    const visualDirection = videoStudioBody(fields.visual_direction, "Visual direction", 5000, true);
    const narration = videoStudioBody(fields.narration, "Narration", 5000, true);
    const onScreenText = videoStudioBody(fields.on_screen_text, "Text trên màn hình", 3000, true);
    const shotNotes = videoStudioBody(fields.shot_notes, "Ghi chú quay dựng", 5000, true);
    const transition = videoStudioLine(fields.transition, "Chuyển cảnh", 0, 500, true);
    const tags = videoStudioTags(fields.tags);
    if (!VIDEO_STUDIO_SCENE_TYPES.has(sceneType)) throw new Error("Vai trò scene không hợp lệ.");
    if (!Number.isInteger(duration) || duration < 1 || duration > 1800) throw new Error("Thời lượng scene cần là số nguyên từ 1 đến 1.800 giây.");
    const safety = videoStudioSafetyError(title, sceneType, visualDirection, narration, onScreenText, shotNotes, transition, ...tags);
    if (safety) throw new Error(safety);
    return {
      title, scene_type: sceneType, duration_seconds: duration, visual_direction: visualDirection,
      narration, on_screen_text: onScreenText, shot_notes: shotNotes, transition, tags
    };
  }
  function videoStudioBoundaryIsSafe(value) {
    const source = value && typeof value === "object" ? value : {};
    const boundary = source.boundary && typeof source.boundary === "object"
      ? source.boundary
      : (source.policy && typeof source.policy === "object" ? source.policy : source);
    return Boolean(
      boundary.execution === "authoring_only"
      && boundary.provider_called === false
      && boundary.video_created === false
    );
  }

  // Image Creative Studio is deliberately separate from `/image/*`.  It is
  // a private art-direction workspace, not an image engine: browser input is
  // metadata plus owned Asset Vault UUIDs only, never URLs/blobs/providers.
  const IMAGE_STUDIO_INTENTS = new Set(["create", "edit", "upscale", "image_to_image", "remove_background"]);
  const IMAGE_STUDIO_ASPECT_RATIOS = new Set(["1:1", "4:5", "3:4", "16:9", "9:16", "3:2", "2:3", "custom"]);
  const IMAGE_STUDIO_OUTPUT_FORMATS = new Set(["png", "jpg", "webp"]);
  const IMAGE_STUDIO_STATES = new Set(["draft", "review", "approved", "archived"]);
  function validImageStudioArtboardId(value) { return validProjectId(value); }
  function validImageStudioDirectionId(value) { return validProjectId(value); }
  function validImageStudioRevision(value) { return validMemoryRevision(value); }
  function imageArtboardIdFromPath(path) {
    const match = /^\/image-studio\/([^/]+)$/.exec(String(path || "").split("?")[0]);
    const id = match ? String(match[1] || "") : "";
    return validImageStudioArtboardId(id) ? id : "";
  }
  function isNativeImageStudioPath(path) {
    const normalized = String(path || "").split("?")[0];
    return normalized === "/image-studio" || normalized === "/image-studio/new" || Boolean(imageArtboardIdFromPath(normalized));
  }
  function imageStudioSecretSafetyError(...values) {
    const text = values.map((value) => String(value || "")).join("\n");
    if (PROMPT_UNSAFE_CONTROL_PATTERN.test(text)) return "Image Creative Studio không nhận ký tự điều khiển không an toàn.";
    const sensitiveKind = supportSensitiveContentKind(text);
    if (sensitiveKind === "manual-payment") return "Image Creative Studio không nhận bill, TXID, QR, số tài khoản hoặc chứng từ thanh toán.";
    if (sensitiveKind || PROMPT_QUOTED_SECRET_PATTERN.test(text) || PROMPT_PRIVATE_KEY_PATTERN.test(text)) return "Image Creative Studio không nhận API key, khóa riêng, token, mật khẩu, OTP/CVV hoặc số thẻ.";
    return "";
  }
  function imageStudioMetadataSafetyError(...values) {
    const secret = imageStudioSecretSafetyError(...values);
    if (secret) return secret;
    const text = values.map((value) => String(value || "")).join("\n");
    if (/(?:file|javascript|data):|https?:\/\/|\bwww\./i.test(text)) return "Image Creative Studio không nhận URL hoặc scheme tệp; hãy chọn Asset Vault reference đã được kiểm tra quyền sở hữu.";
    if (/\b(?:(?:provider|engine|image|render|preview|job|media|file)[ _-]*(?:id|ref(?:erence)?|token)|telegram[ _-]*file[ _-]*id)\b\s*(?::|=|\bis\b)\s*\S+/i.test(text)) return "Image Creative Studio không nhận provider, engine, Bot, job hoặc file handle trong metadata.";
    return "";
  }
  function imageStudioLine(value, label, minimum, maximum, allowEmpty) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (text.length > maximum || (!allowEmpty && text.length < minimum) || text.includes("\u0000")) throw new Error(label + " cần từ " + minimum + " đến " + maximum + " ký tự hợp lệ.");
    return text;
  }
  function imageStudioBody(value, label, maximum, allowEmpty) {
    const text = String(value || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
    if (text.length > maximum || (!allowEmpty && !text) || text.includes("\u0000")) throw new Error(label + " tối đa " + maximum.toLocaleString("vi-VN") + " ký tự hợp lệ.");
    return text;
  }
  function imageStudioTags(value) {
    const raw = Array.isArray(value) ? value : String(value || "").split(",");
    const result = [];
    const seen = new Set();
    raw.forEach((candidate) => {
      if (!String(candidate || "").trim()) return;
      const tag = imageStudioLine(candidate, "Tag", 1, 48, false);
      const fingerprint = tag.toLocaleLowerCase("vi-VN");
      if (!seen.has(fingerprint)) { seen.add(fingerprint); result.push(tag); }
    });
    if (result.length > 20) throw new Error("Tối đa 20 tags cho mỗi artboard hoặc biến thể direction.");
    return result;
  }
  function imageStudioReference(value, label, allowEmpty) {
    const id = String(value || "").trim();
    if (!id && allowEmpty) return "";
    if (!validImageStudioArtboardId(id)) throw new Error(label + " phải là Asset Vault/Project UUID hợp lệ do server cấp.");
    return id;
  }
  function imageArtboardPayload(fields) {
    const title = imageStudioLine(fields.title, "Tên artboard", 2, 180, false);
    const imageIntent = imageStudioLine(fields.image_intent || "create", "Ý định direction", 1, 32, false).toLowerCase();
    const language = imageStudioLine(fields.language || "vi", "Ngôn ngữ direction", 1, 100, false);
    const aspectRatio = imageStudioLine(fields.aspect_ratio || "1:1", "Tỷ lệ khung hình", 1, 32, false);
    const outputFormat = imageStudioLine(fields.output_format || "png", "Định dạng đích", 1, 16, false).toLowerCase();
    const creativeBrief = imageStudioBody(fields.creative_brief, "Creative brief", 12000, false);
    const styleDirection = imageStudioBody(fields.style_direction, "Style direction", 6000, true);
    const negativeDirection = imageStudioBody(fields.negative_direction, "Điều cần tránh", 4000, true);
    const tags = imageStudioTags(fields.tags);
    if (!IMAGE_STUDIO_INTENTS.has(imageIntent)) throw new Error("Ý định Image Studio không hợp lệ.");
    if (!IMAGE_STUDIO_ASPECT_RATIOS.has(aspectRatio)) throw new Error("Tỷ lệ khung hình Image Studio không hợp lệ.");
    if (!IMAGE_STUDIO_OUTPUT_FORMATS.has(outputFormat)) throw new Error("Định dạng đích Image Studio không hợp lệ.");
    const safety = imageStudioMetadataSafetyError(title, imageIntent, language, aspectRatio, outputFormat, creativeBrief, styleDirection, negativeDirection, ...tags);
    if (safety) throw new Error(safety);
    return { title, image_intent: imageIntent, language, aspect_ratio: aspectRatio, output_format: outputFormat, creative_brief: creativeBrief, style_direction: styleDirection, negative_direction: negativeDirection, tags, project_id: imageStudioReference(fields.project_id, "Project liên kết", true) || null };
  }
  function imageDirectionPayload(fields) {
    const title = imageStudioLine(fields.title, "Tên biến thể direction", 2, 180, false);
    const operation = imageStudioLine(fields.operation || "create", "Loại biến thể", 1, 32, false).toLowerCase();
    const promptText = imageStudioBody(fields.prompt_text, "Prompt / concept text", 12000, true);
    const editInstructions = imageStudioBody(fields.edit_instructions, "Chỉ dẫn chỉnh sửa", 6000, true);
    const compositionNotes = imageStudioBody(fields.composition_notes, "Bố cục & visual notes", 6000, true);
    const negativeDirection = imageStudioBody(fields.negative_direction, "Điều cần tránh", 4000, true);
    const assetId = imageStudioReference(fields.asset_id, "Ảnh gốc Asset Vault", true);
    const referenceAssetId = imageStudioReference(fields.reference_asset_id, "Ảnh tham chiếu Asset Vault", true);
    const tags = imageStudioTags(fields.tags);
    if (!IMAGE_STUDIO_INTENTS.has(operation)) throw new Error("Loại biến thể Image Studio không hợp lệ.");
    if (operation !== "create" && !assetId) throw new Error("Edit, Upscale, Image-to-image và Tách nền cần chọn ảnh gốc từ Asset Vault.");
    // Keep browser validation aligned with the server's operation contract so
    // a valid-looking form cannot turn into a preventable 422 receipt.
    if (operation === "create" && !promptText) throw new Error("Create direction cần prompt / concept text.");
    if (["edit", "image_to_image"].includes(operation) && !promptText && !editInstructions) throw new Error("Edit và Image-to-image cần prompt hoặc chỉ dẫn chỉnh sửa.");
    if (["upscale", "remove_background"].includes(operation) && !promptText && !editInstructions && !compositionNotes) throw new Error("Upscale và Tách nền cần prompt, chỉ dẫn chỉnh sửa hoặc visual note.");
    const safety = imageStudioMetadataSafetyError(title, operation, promptText, editInstructions, compositionNotes, negativeDirection, ...tags);
    if (safety) throw new Error(safety);
    return { title, operation, prompt_text: promptText, edit_instructions: editInstructions, composition_notes: compositionNotes, negative_direction: negativeDirection, asset_id: assetId || null, reference_asset_id: referenceAssetId || null, tags };
  }
  function imageStudioBoundaryIsSafe(value) {
    const source = value && typeof value === "object" ? value : {};
    const boundary = source.boundary && typeof source.boundary === "object" ? source.boundary : (source.policy && typeof source.policy === "object" ? source.policy : source);
    return Boolean(
      boundary.execution === "authoring_only"
      && boundary.provider_called === false
      && boundary.image_created === false
      && boundary.output_created === false
      && boundary.media_uploads === false
      && boundary.browser_media_url === false
      && boundary.preview_available === false
      && boundary.job_created === false
      && boundary.wallet_mutated === false
      && boundary.payment_started === false
      && boundary.payment_processed === false
      && boundary.output_delivery === "guarded"
    );
  }

  // AI Chat Workspace is a deliberately no-engine authoring boundary. It
  // accepts only owner-scoped conversation metadata and human-authored text;
  // no model/system prompt/provider/Bot/wallet/job field exists in this API.
  const CHAT_WORKSPACE_MODES = new Set(["focus", "deep", "pro"]);
  const CHAT_WORKSPACE_STATES = new Set(["draft", "review", "ready", "archived"]);
  const CHAT_CONTEXT_KINDS = new Set(["brief", "constraint", "reference", "instruction"]);
  const CHAT_TURN_KINDS = new Set(["prompt", "note", "decision"]);
  function validChatWorkspaceId(value) { return validProjectId(value); }
  function validChatWorkspaceRevision(value) { return validMemoryRevision(value); }
  function chatThreadIdFromPath(path) {
    const match = /^\/chat\/([^/]+)$/.exec(String(path || "").split("?")[0]);
    const id = match ? String(match[1] || "") : "";
    return validChatWorkspaceId(id) ? id : "";
  }
  function isNativeChatWorkspacePath(path) {
    const normalized = String(path || "").split("?")[0];
    return normalized === "/chat" || normalized === "/chat/new" || Boolean(chatThreadIdFromPath(normalized));
  }
  function chatWorkspaceSafetyError(...values) {
    const text = values.map((value) => String(value || "")).join("\n");
    if (PROMPT_UNSAFE_CONTROL_PATTERN.test(text)) return "AI Chat Workspace không nhận ký tự điều khiển không an toàn.";
    const sensitiveKind = supportSensitiveContentKind(text);
    if (sensitiveKind === "manual-payment") return "AI Chat Workspace không nhận bill, TXID, QR, số tài khoản hoặc chứng từ thanh toán.";
    if (sensitiveKind || PROMPT_QUOTED_SECRET_PATTERN.test(text) || PROMPT_PRIVATE_KEY_PATTERN.test(text)) return "AI Chat Workspace không nhận API key, khóa riêng, token, mật khẩu, OTP/CVV hoặc số thẻ.";
    if (/(?:file|javascript|data|blob):|https?:\/\/|\bwww\.|(?:^|[\s\"'(])(?:[A-Za-z]:[\\/]|\\\\[^\s]+|\/[^\s]+)/i.test(text)) return "AI Chat Workspace không nhận URL, path, blob hoặc scheme tệp.";
    if (/\b(?:(?:provider|engine|telegram|bot|job|worker|media|asset|file)[ _-]*(?:id|ref(?:erence)?|token|handle)|storage[ _-]*key)\b\s*(?::|=|\bis\b)\s*\S+/i.test(text)) return "AI Chat Workspace không nhận provider, Bot, job, worker hoặc file handle trong metadata.";
    return "";
  }
  function chatWorkspaceLine(value, label, minimum, maximum, allowEmpty) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (text.length > maximum || (!allowEmpty && text.length < minimum) || text.includes("\u0000")) throw new Error(label + " cần từ " + minimum + " đến " + maximum + " ký tự hợp lệ.");
    return text;
  }
  function chatWorkspaceBody(value, label, maximum, allowEmpty) {
    const text = String(value || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
    if (text.length > maximum || (!allowEmpty && !text) || text.includes("\u0000")) throw new Error(label + " tối đa " + maximum.toLocaleString("vi-VN") + " ký tự hợp lệ.");
    return text;
  }
  function chatWorkspaceTags(value) {
    const raw = Array.isArray(value) ? value : String(value || "").split(",");
    const result = [];
    const seen = new Set();
    raw.forEach((candidate) => {
      if (!String(candidate || "").trim()) return;
      const tag = chatWorkspaceLine(candidate, "Tag", 1, 48, false);
      const fingerprint = tag.toLocaleLowerCase("vi-VN");
      if (!seen.has(fingerprint)) { seen.add(fingerprint); result.push(tag); }
    });
    if (result.length > 20) throw new Error("Tối đa 20 tags cho mỗi thread hoặc context card.");
    return result;
  }
  function chatWorkspaceReference(value, label) {
    const id = String(value || "").trim();
    if (!id) return null;
    if (!validChatWorkspaceId(id)) throw new Error(label + " phải là UUID owner-scoped do server cấp.");
    return id;
  }
  function chatThreadPayload(fields) {
    const title = chatWorkspaceLine(fields.title, "Tên hội thoại", 3, 180, false);
    const objective = chatWorkspaceBody(fields.objective, "Mục tiêu", 8000, false);
    const mode = chatWorkspaceLine(fields.mode || "focus", "Cách biên tập", 1, 24, false).toLowerCase();
    const systemContext = chatWorkspaceBody(fields.system_context, "Ngữ cảnh làm việc", 12000, true);
    const tags = chatWorkspaceTags(fields.tags);
    if (!CHAT_WORKSPACE_MODES.has(mode)) throw new Error("Cách biên tập cục bộ không hợp lệ.");
    const safety = chatWorkspaceSafetyError(title, objective, systemContext, mode, ...tags);
    if (safety) throw new Error(safety);
    return { title, objective, mode, system_context: systemContext, tags, project_id: chatWorkspaceReference(fields.project_id, "Project liên kết"), prompt_template_id: chatWorkspaceReference(fields.prompt_template_id, "Prompt Library liên kết"), pinned: fields.pinned === true || fields.pinned === "true" };
  }
  function chatContextPayload(fields) {
    const kind = chatWorkspaceLine(fields.kind || "brief", "Loại context", 1, 32, false).toLowerCase();
    const title = chatWorkspaceLine(fields.title, "Tiêu đề context", 2, 180, false);
    const body = chatWorkspaceBody(fields.body, "Nội dung context", 12000, false);
    const tags = chatWorkspaceTags(fields.tags);
    if (!CHAT_CONTEXT_KINDS.has(kind)) throw new Error("Loại context không hợp lệ.");
    const safety = chatWorkspaceSafetyError(kind, title, body, ...tags);
    if (safety) throw new Error(safety);
    return { kind, title, body, tags };
  }
  function chatTurnPayload(fields) {
    const kind = chatWorkspaceLine(fields.kind || "prompt", "Loại lượt", 1, 32, false).toLowerCase();
    const body = chatWorkspaceBody(fields.body, "Nội dung lượt", 16000, false);
    if (!CHAT_TURN_KINDS.has(kind)) throw new Error("Loại lượt không hợp lệ.");
    const safety = chatWorkspaceSafetyError(kind, body);
    if (safety) throw new Error(safety);
    return { kind, body };
  }
  function chatWorkspaceBoundaryIsSafe(value) {
    const source = value && typeof value === "object" ? value : {};
    const boundary = source.boundary && typeof source.boundary === "object" ? source.boundary : (source.policy && typeof source.policy === "object" ? source.policy : source);
    return Boolean(
      boundary.execution === "authoring_only"
      && boundary.ai_execution_available === false
      && boundary.provider_called === false
      && boundary.bot_called === false
      && boundary.assistant_reply_created === false
      && boundary.output_created === false
      && boundary.job_created === false
      && boundary.payment_started === false
      && boundary.wallet_mutated === false
      && boundary.payment_processed === false
      && boundary.browser_file_upload === false
      && boundary.browser_media_url === false
      && boundary.stream_available === false
      && boundary.output_delivery === "guarded"
    );
  }

  // Analytics Workspace is intentionally limited to manual measurements
  // written by the signed Web account.  It never accepts a platform URL,
  // provider/Bot handle, payment reference or a browser-imported dataset.
  const ANALYTICS_REPORT_STATES = new Set(["draft", "review", "finalized", "archived"]);
  const ANALYTICS_METRIC_STATES = new Set(["active", "archived"]);
  const ANALYTICS_METRIC_UNITS = new Set(["count", "percent", "duration", "custom"]);
  const ANALYTICS_METRIC_DIRECTIONS = new Set(["up", "down", "neutral"]);
  const ANALYTICS_FINDING_KINDS = new Set(["finding", "decision", "action"]);
  const ANALYTICS_FINDING_STATES = new Set(["active", "archived"]);
  function validAnalyticsWorkspaceId(value) { return validProjectId(value); }
  function validAnalyticsRevision(value) { return validMemoryRevision(value); }
  function analyticsReportIdFromPath(path) {
    const match = /^\/analytics\/([^/]+)$/.exec(String(path || "").split("?")[0]);
    const id = match ? String(match[1] || "") : "";
    return validAnalyticsWorkspaceId(id) ? id : "";
  }
  function isNativeAnalyticsWorkspacePath(path) {
    const normalized = String(path || "").split("?")[0];
    return normalized === "/analytics" || normalized === "/analytics/new" || Boolean(analyticsReportIdFromPath(normalized));
  }
  function analyticsWorkspaceSafetyError(...values) {
    const text = values.map((value) => String(value || "")).join("\n");
    if (PROMPT_UNSAFE_CONTROL_PATTERN.test(text)) return "Analytics Workspace không nhận ký tự điều khiển không an toàn.";
    const sensitiveKind = supportSensitiveContentKind(text);
    if (sensitiveKind === "manual-payment") return "Analytics Workspace không nhận bill, TXID, QR, số tài khoản hoặc chứng từ thanh toán.";
    if (sensitiveKind || PROMPT_QUOTED_SECRET_PATTERN.test(text) || PROMPT_PRIVATE_KEY_PATTERN.test(text)) return "Analytics Workspace không nhận API key, khóa riêng, token, mật khẩu, OTP/CVV hoặc số thẻ.";
    if (/(?:file|javascript|data|blob):|https?:\/\/|\bwww\.|(?:^|[\s\"'(])(?:[A-Za-z]:[\\/]|\\\\[^\s]+|\/[^\s]+)/i.test(text)) return "Analytics Workspace không nhận URL, path, blob hoặc scheme tệp.";
    if (/\b(?:(?:provider|engine|telegram|bot|job|worker|media|asset|file|platform|channel)[ _-]*(?:id|ref(?:erence)?|token|handle)|storage[ _-]*key)\b\s*(?::|=|\bis\b)\s*\S+/i.test(text)) return "Analytics Workspace không nhận provider, Bot, job, worker, nền tảng hoặc file handle trong metadata.";
    if (/<\s*\/?\s*(?:script|svg|img|iframe|object|embed|style|link|meta|base|form|input|video|audio)\b|\bon[a-z]+\s*=/i.test(text)) return "Analytics Workspace không nhận markup hoặc lệnh thực thi.";
    return "";
  }
  function analyticsWorkspaceLine(value, label, minimum, maximum, allowEmpty) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (text.length > maximum || (!allowEmpty && text.length < minimum) || text.includes("\u0000")) throw new Error(label + " cần từ " + minimum + " đến " + maximum + " ký tự hợp lệ.");
    if (text && /^\s*[=+@]/.test(text)) throw new Error(label + " không nhận công thức hoặc biểu thức xuất dữ liệu.");
    return text;
  }
  function analyticsWorkspaceBody(value, label, maximum, allowEmpty) {
    const text = String(value || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
    if (text.length > maximum || (!allowEmpty && !text) || text.includes("\u0000")) throw new Error(label + " tối đa " + maximum.toLocaleString("vi-VN") + " ký tự hợp lệ.");
    return text;
  }
  function analyticsWorkspaceTags(value) {
    const raw = Array.isArray(value) ? value : String(value || "").split(",");
    const result = [];
    const seen = new Set();
    raw.forEach((candidate) => {
      if (!String(candidate || "").trim()) return;
      const tag = analyticsWorkspaceLine(candidate, "Tag", 1, 48, false);
      const safety = analyticsWorkspaceSafetyError(tag);
      if (safety) throw new Error(safety);
      const marker = tag.toLocaleLowerCase("vi-VN");
      if (!seen.has(marker)) { seen.add(marker); result.push(tag); }
    });
    if (result.length > 20) throw new Error("Tối đa 20 tags cho mỗi report.");
    return result;
  }
  function analyticsWorkspaceReference(value, label) {
    const id = String(value || "").trim();
    if (!id) return null;
    if (!validAnalyticsWorkspaceId(id)) throw new Error(label + " phải là UUID owner-scoped do server cấp.");
    return id;
  }
  function analyticsWorkspaceDate(value, label) {
    const text = String(value || "").trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) throw new Error(label + " phải có dạng YYYY-MM-DD.");
    const parsed = new Date(text + "T00:00:00.000Z");
    if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== text) throw new Error(label + " không hợp lệ.");
    return { text, time: parsed.getTime() };
  }
  function analyticsWorkspaceDecimal(value) {
    const text = String(value || "").trim();
    if (!/^\d+(?:\.\d+)?$/.test(text) || text.length > 40) throw new Error("Giá trị metric phải là số thập phân không âm theo dạng thường.");
    const parsed = Number(text);
    if (!Number.isFinite(parsed) || parsed < 0 || parsed > 1000000000000) throw new Error("Giá trị metric nằm ngoài giới hạn an toàn.");
    return text;
  }
  function analyticsReportPayload(fields) {
    const title = analyticsWorkspaceLine(fields.title, "Tên báo cáo", 3, 180, false);
    const objective = analyticsWorkspaceBody(fields.objective, "Mục tiêu đo lường", 2000, false);
    const contextLabel = analyticsWorkspaceLine(fields.context_label, "Nhãn bối cảnh", 0, 160, true);
    const start = analyticsWorkspaceDate(fields.period_start, "Bắt đầu kỳ");
    const end = analyticsWorkspaceDate(fields.period_end, "Kết thúc kỳ");
    if (end.time < start.time || (end.time - start.time) / 86400000 > 366) throw new Error("Khoảng thời gian phải theo thứ tự hợp lệ và không quá 366 ngày.");
    const summaryNote = analyticsWorkspaceBody(fields.summary_note, "Ghi chú tổng quan", 6000, true);
    const tags = analyticsWorkspaceTags(fields.tags);
    const safety = analyticsWorkspaceSafetyError(title, objective, contextLabel, summaryNote, ...tags);
    if (safety) throw new Error(safety);
    return { title, objective, context_label: contextLabel, period_start: start.text, period_end: end.text, project_id: analyticsWorkspaceReference(fields.project_id, "Project liên kết"), campaign_plan_id: analyticsWorkspaceReference(fields.campaign_plan_id, "Campaign Planner liên kết"), tags, summary_note: summaryNote };
  }
  function analyticsMetricPayload(fields) {
    const name = analyticsWorkspaceLine(fields.name, "Tên metric", 2, 120, false);
    const unit = analyticsWorkspaceLine(fields.unit || "count", "Đơn vị metric", 1, 20, false).toLowerCase();
    const direction = analyticsWorkspaceLine(fields.direction || "neutral", "Chiều đánh giá", 1, 20, false).toLowerCase();
    const description = analyticsWorkspaceBody(fields.description, "Ghi chú metric", 1200, true);
    if (!ANALYTICS_METRIC_UNITS.has(unit) || !ANALYTICS_METRIC_DIRECTIONS.has(direction)) throw new Error("Đơn vị hoặc chiều theo dõi metric không hợp lệ.");
    const safety = analyticsWorkspaceSafetyError(name, unit, direction, description);
    if (safety) throw new Error(safety);
    return { name, unit, direction, description };
  }
  function analyticsSnapshotPayload(fields) {
    const observed = analyticsWorkspaceDate(fields.observed_on, "Ngày quan sát");
    const value = analyticsWorkspaceDecimal(fields.value);
    const sourceLabel = analyticsWorkspaceLine(fields.source_label, "Nhãn nguồn tự khai", 0, 160, true);
    const note = analyticsWorkspaceBody(fields.note, "Ghi chú snapshot", 1800, true);
    const safety = analyticsWorkspaceSafetyError(sourceLabel, note);
    if (safety) throw new Error(safety);
    return { observed_on: observed.text, value, source_label: sourceLabel, note };
  }
  function analyticsFindingPayload(fields) {
    const kind = analyticsWorkspaceLine(fields.kind || "finding", "Loại nhận định", 1, 20, false).toLowerCase();
    const body = analyticsWorkspaceBody(fields.body, "Nội dung nhận định", 6000, false);
    if (!ANALYTICS_FINDING_KINDS.has(kind)) throw new Error("Loại nhận định không hợp lệ.");
    const safety = analyticsWorkspaceSafetyError(kind, body);
    if (safety) throw new Error(safety);
    return { kind, body };
  }
  function analyticsWorkspaceBoundaryIsSafe(value) {
    const source = value && typeof value === "object" ? value : {};
    const boundary = source.boundary && typeof source.boundary === "object" ? source.boundary : (source.policy && typeof source.policy === "object" ? source.policy : source);
    return Boolean(
      boundary.execution === "manual_measurement_only"
      && boundary.data_origin === "user_supplied_only"
      && boundary.local_calculation === true
      && boundary.bot_called === false
      && boundary.provider_called === false
      && boundary.social_api_called === false
      && boundary.platform_data_connected === false
      && boundary.platform_data_verified === false
      && boundary.ai_recommendation_created === false
      && boundary.canonical_revenue === false
      && boundary.wallet_mutated === false
      && boundary.payment_started === false
      && boundary.payment_processed === false
      && boundary.job_created === false
      && boundary.publish_action_created === false
      && boundary.browser_file_upload === false
      && boundary.external_url_import === false
      && boundary.report_file_created === false
      && boundary.output_delivery === "not_applicable"
    );
  }

  // Document & PDF Workspace holds signed-account briefs and plan metadata
  // only.  It never turns an Asset Vault UUID into an upload/source read,
  // OCR/translation/conversion request, job, output or payment action.
  const DOCUMENT_WORKSPACE_TYPES = new Set(["mixed", "pdf", "office", "text", "image", "scan"]);
  const DOCUMENT_WORKSPACE_OPERATIONS = new Set([
    "organize", "split", "merge", "optimize", "image_to_pdf", "pdf_to_images",
    "pdf_to_word", "ocr", "translate", "convert", "other"
  ]);
  const DOCUMENT_WORKSPACE_STATES = new Set(["draft", "review", "approved", "archived"]);
  function validDocumentWorkspaceId(value) { return validProjectId(value); }
  function validDocumentPlanId(value) { return validProjectId(value); }
  function validDocumentWorkspaceRevision(value) { return validMemoryRevision(value); }
  function documentWorkspaceIdFromPath(path) {
    const match = /^\/document-workspace\/([^/]+)$/.exec(String(path || "").split("?")[0]);
    const id = match ? String(match[1] || "") : "";
    return validDocumentWorkspaceId(id) ? id : "";
  }
  function isNativeDocumentWorkspacePath(path) {
    const normalized = String(path || "").split("?")[0];
    return normalized === "/document-workspace" || normalized === "/document-workspace/new" || Boolean(documentWorkspaceIdFromPath(normalized));
  }
  function documentWorkspaceSafetyError(...values) {
    const text = values.map((value) => String(value || "")).join("\n");
    if (PROMPT_UNSAFE_CONTROL_PATTERN.test(text)) return "Document & PDF Workspace không nhận ký tự điều khiển không an toàn.";
    const sensitiveKind = supportSensitiveContentKind(text);
    if (sensitiveKind === "manual-payment") return "Document & PDF Workspace không nhận bill, TXID, QR, số tài khoản hoặc chứng từ thanh toán.";
    if (sensitiveKind || PROMPT_QUOTED_SECRET_PATTERN.test(text) || PROMPT_PRIVATE_KEY_PATTERN.test(text)) return "Document & PDF Workspace không nhận API key, khóa riêng, token, mật khẩu, OTP/CVV hoặc số thẻ.";
    if (/(?:file|javascript|data):|https?:\/\/|\bwww\./i.test(text)) return "Document & PDF Workspace không nhận URL hoặc scheme tệp; hãy chọn Asset Vault reference đã được kiểm tra quyền sở hữu.";
    if (/\b(?:(?:provider|engine|telegram|bot|job|worker)[ _-]*(?:id|ref(?:erence)?|token|handle)|storage[ _-]*key)\b\s*(?::|=|\bis\b)\s*\S+/i.test(text)) return "Document & PDF Workspace không nhận provider, Bot, job, worker hoặc file handle trong metadata.";
    return "";
  }
  function documentWorkspaceLine(value, label, minimum, maximum, allowEmpty) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (text.length > maximum || (!allowEmpty && text.length < minimum) || text.includes("\u0000")) throw new Error(label + " cần từ " + minimum + " đến " + maximum + " ký tự hợp lệ.");
    return text;
  }
  function documentWorkspaceBody(value, label, maximum, allowEmpty) {
    const text = String(value || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
    if (text.length > maximum || (!allowEmpty && !text) || text.includes("\u0000")) throw new Error(label + " tối đa " + maximum.toLocaleString("vi-VN") + " ký tự hợp lệ.");
    return text;
  }
  function documentWorkspaceTags(value) {
    const raw = Array.isArray(value) ? value : String(value || "").split(",");
    const result = [];
    const seen = new Set();
    raw.forEach((candidate) => {
      if (!String(candidate || "").trim()) return;
      const tag = documentWorkspaceLine(candidate, "Tag", 1, 48, false);
      const fingerprint = tag.toLocaleLowerCase("vi-VN");
      if (!seen.has(fingerprint)) { seen.add(fingerprint); result.push(tag); }
    });
    if (result.length > 20) throw new Error("Tối đa 20 tags cho mỗi document brief hoặc processing plan.");
    return result;
  }
  function documentWorkspaceReference(value, label, allowEmpty) {
    const id = String(value || "").trim();
    if (!id && allowEmpty) return "";
    if (!validDocumentWorkspaceId(id)) throw new Error(label + " phải là Project/Asset Vault UUID hợp lệ do server cấp.");
    return id;
  }
  function documentWorkspacePayload(fields) {
    const title = documentWorkspaceLine(fields.title, "Tên document brief", 2, 180, false);
    const documentType = documentWorkspaceLine(fields.document_type || "mixed", "Loại tài liệu", 1, 32, false).toLowerCase();
    const sourceSummary = documentWorkspaceBody(fields.source_summary, "Scope, nguồn & trang dự kiến", 8000, false);
    const objective = documentWorkspaceBody(fields.objective, "Mục tiêu, target format & QA checklist", 8000, false);
    const language = documentWorkspaceLine(fields.language || "vi", "Ngôn ngữ nguồn", 1, 100, false);
    const targetLanguage = documentWorkspaceLine(fields.target_language, "Ngôn ngữ đích", 1, 100, true);
    const tags = documentWorkspaceTags(fields.tags);
    if (!DOCUMENT_WORKSPACE_TYPES.has(documentType)) throw new Error("Loại tài liệu Document Workspace không hợp lệ.");
    const safety = documentWorkspaceSafetyError(title, documentType, sourceSummary, objective, language, targetLanguage, ...tags);
    if (safety) throw new Error(safety);
    return { title, document_type: documentType, source_summary: sourceSummary, objective, language, target_language: targetLanguage, tags, project_id: documentWorkspaceReference(fields.project_id, "Project liên kết", true) || null };
  }
  function documentPlanPayload(fields) {
    const title = documentWorkspaceLine(fields.title, "Tên processing plan", 2, 180, false);
    const operation = documentWorkspaceLine(fields.operation || "organize", "Intent / planned operation", 1, 32, false).toLowerCase();
    const instructions = documentWorkspaceBody(fields.instructions, "Scope, pages & kiểm tra dự kiến", 12000, true);
    const sourceAssetId = documentWorkspaceReference(fields.source_asset_id, "Source Asset Vault", true);
    const referenceAssetId = documentWorkspaceReference(fields.reference_asset_id, "Reference Asset Vault", true);
    const tags = documentWorkspaceTags(fields.tags);
    if (!DOCUMENT_WORKSPACE_OPERATIONS.has(operation)) throw new Error("Intent Document Workspace không hợp lệ.");
    if (sourceAssetId && sourceAssetId === referenceAssetId) throw new Error("Source Asset Vault và Reference Asset Vault phải khác nhau.");
    const safety = documentWorkspaceSafetyError(title, operation, instructions, ...tags);
    if (safety) throw new Error(safety);
    return { title, operation, instructions, source_asset_id: sourceAssetId || null, reference_asset_id: referenceAssetId || null, tags };
  }
  function documentWorkspaceBoundaryIsSafe(value) {
    const source = value && typeof value === "object" ? value : {};
    const boundary = source.boundary && typeof source.boundary === "object" ? source.boundary : (source.policy && typeof source.policy === "object" ? source.policy : source);
    return Boolean(
      boundary.execution === "authoring_only"
      && boundary.provider_called === false
      && boundary.ocr_called === false
      && boundary.translation_called === false
      && boundary.output_created === false
      && boundary.job_created === false
      && boundary.payment_started === false
      && boundary.wallet_mutated === false
      && boundary.payment_processed === false
      && boundary.browser_file_upload === false
      && boundary.browser_media_url === false
      && boundary.preview_available === false
      && boundary.output_delivery === "guarded"
    );
  }

  // Subtitle & Transcript Workspace is a separate text-authoring boundary.
  // Unlike a media pipeline it accepts no upload/source/provider/job/file
  // reference.  Cue text may legitimately contain an uttered/displayed URL;
  // it stays escaped plain text in the portal and is never a clickable or
  // fetchable source. Project metadata and editor notes remain stricter.
  const SUBTITLE_STUDIO_FORMATS = new Set(["srt", "vtt"]);
  const SUBTITLE_STUDIO_INTENTS = new Set(["subtitle", "translation", "asr_review", "dubbing_direction"]);
  const SUBTITLE_STUDIO_PROJECT_STATES = new Set(["draft", "review", "approved", "archived"]);
  function validSubtitleStudioProjectId(value) { return validProjectId(value); }
  function validSubtitleStudioCueId(value) { return validProjectId(value); }
  function validSubtitleStudioRevision(value) { return validMemoryRevision(value); }
  function subtitleProjectIdFromPath(path) {
    const match = /^\/subtitle-studio\/([^/]+)$/.exec(String(path || "").split("?")[0]);
    const id = match ? String(match[1] || "") : "";
    return validSubtitleStudioProjectId(id) ? id : "";
  }
  function isNativeSubtitleStudioPath(path) {
    const normalized = String(path || "").split("?")[0];
    return normalized === "/subtitle-studio" || normalized === "/subtitle-studio/new" || Boolean(subtitleProjectIdFromPath(normalized));
  }
  function subtitleStudioSecretSafetyError(...values) {
    const text = values.map((value) => String(value || "")).join("\n");
    if (PROMPT_UNSAFE_CONTROL_PATTERN.test(text)) return "Subtitle Studio không nhận ký tự điều khiển không an toàn.";
    const sensitiveKind = supportSensitiveContentKind(text);
    if (sensitiveKind === "manual-payment") return "Subtitle Studio không nhận bill, TXID, QR, số tài khoản hoặc chứng từ thanh toán.";
    if (sensitiveKind || PROMPT_QUOTED_SECRET_PATTERN.test(text) || PROMPT_PRIVATE_KEY_PATTERN.test(text)) return "Subtitle Studio không nhận API key, khóa riêng, token, mật khẩu, OTP/CVV hoặc số thẻ.";
    return "";
  }
  function subtitleStudioMetadataSafetyError(...values) {
    const secret = subtitleStudioSecretSafetyError(...values);
    if (secret) return secret;
    const text = values.map((value) => String(value || "")).join("\n");
    if (/(?:file|javascript|data):|https?:\/\/|\bwww\./i.test(text)) return "Metadata Subtitle Studio không nhận URL hoặc scheme tệp.";
    if (/\b(?:(?:provider|asr|tts|dub(?:bing)?|translation|job|media|file)[ _-]*(?:id|ref(?:erence)?|token)|telegram[ _-]*file[ _-]*id)\b\s*(?::|=|\bis\b)\s*\S+/i.test(text)) return "Metadata Subtitle Studio không nhận provider, engine, Bot, job hoặc file handle.";
    return "";
  }
  function subtitleStudioLine(value, label, minimum, maximum, allowEmpty) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (text.length > maximum || (!allowEmpty && text.length < minimum) || text.includes("\u0000")) throw new Error(label + " cần từ " + minimum + " đến " + maximum + " ký tự hợp lệ.");
    return text;
  }
  function subtitleStudioBody(value, label, maximum, allowEmpty) {
    const text = String(value || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
    if (text.length > maximum || (!allowEmpty && !text) || text.includes("\u0000")) throw new Error(label + " tối đa " + maximum.toLocaleString("vi-VN") + " ký tự hợp lệ.");
    return text;
  }
  function subtitleStudioTags(value) {
    const raw = Array.isArray(value) ? value : String(value || "").split(",");
    const result = [];
    const seen = new Set();
    raw.forEach((candidate) => {
      if (!String(candidate || "").trim()) return;
      const tag = subtitleStudioLine(candidate, "Tag", 1, 48, false);
      const fingerprint = tag.toLocaleLowerCase("vi-VN");
      if (!seen.has(fingerprint)) { seen.add(fingerprint); result.push(tag); }
    });
    if (result.length > 20) throw new Error("Tối đa 20 tags cho mỗi transcript project.");
    return result;
  }
  function subtitleStudioReference(value, label) {
    const id = String(value || "").trim();
    if (id && !validSubtitleStudioProjectId(id)) throw new Error(label + " không hợp lệ.");
    return id;
  }
  function subtitleProjectPayload(fields) {
    const title = subtitleStudioLine(fields.title, "Tên transcript project", 2, 180, false);
    const sourceLanguage = subtitleStudioLine(fields.source_language || "vi", "Ngôn ngữ nguồn", 1, 100, false);
    const targetLanguage = subtitleStudioLine(fields.target_language || "en", "Ngôn ngữ bản nháp", 1, 100, false);
    const intent = subtitleStudioLine(fields.intent || "subtitle", "Mục đích workspace", 1, 32, false).toLowerCase();
    const captionFormat = subtitleStudioLine(fields.caption_format || "srt", "Chuẩn preview", 1, 16, false).toLowerCase();
    const context = subtitleStudioBody(fields.context, "Review context", 5000, true);
    const tags = subtitleStudioTags(fields.tags);
    if (!SUBTITLE_STUDIO_INTENTS.has(intent)) throw new Error("Mục đích Subtitle Studio không hợp lệ.");
    if (!SUBTITLE_STUDIO_FORMATS.has(captionFormat)) throw new Error("Chuẩn preview subtitle không hợp lệ.");
    const safety = subtitleStudioMetadataSafetyError(title, sourceLanguage, targetLanguage, intent, captionFormat, context, ...tags);
    if (safety) throw new Error(safety);
    return {
      title, source_language: sourceLanguage, target_language: targetLanguage, intent, caption_format: captionFormat,
      context, tags, project_id: subtitleStudioReference(fields.project_id, "Project liên kết") || null
    };
  }
  function subtitleCuePayload(fields) {
    const startMs = Number(fields.start_ms);
    const endMs = Number(fields.end_ms);
    const speaker = subtitleStudioLine(fields.speaker, "Người nói", 0, 120, true);
    const sourceText = subtitleStudioBody(fields.source_text, "Caption nguồn", 5000, false);
    const translatedText = subtitleStudioBody(fields.translated_text, "Bản nháp ngôn ngữ", 5000, true);
    const notes = subtitleStudioBody(fields.notes, "Ghi chú biên tập", 2000, true);
    if (!Number.isInteger(startMs) || startMs < 0 || startMs > 86399999 || !Number.isInteger(endMs) || endMs < 1 || endMs > 86400000 || endMs <= startMs) {
      throw new Error("Timing cue cần là mili-giây hợp lệ, kết thúc phải sau bắt đầu.");
    }
    // Source/translated text can contain URLs which are merely words shown in
    // a caption.  They are still checked for secrets/payment markers, then
    // rendered with `safeText`; only speaker/notes get metadata URL guards.
    const cueSafety = subtitleStudioSecretSafetyError(sourceText, translatedText);
    if (cueSafety) throw new Error(cueSafety);
    const metadataSafety = subtitleStudioMetadataSafetyError(speaker, notes);
    if (metadataSafety) throw new Error(metadataSafety);
    return { start_ms: startMs, end_ms: endMs, speaker, source_text: sourceText, translated_text: translatedText, notes };
  }
  function subtitleTextImportPayload(fields) {
    const format = subtitleStudioLine(fields.format || "srt", "Chuẩn văn bản", 1, 16, false).toLowerCase();
    const text = subtitleStudioBody(fields.text, "Nội dung SRT/VTT", 60000, false);
    if (!SUBTITLE_STUDIO_FORMATS.has(format)) throw new Error("Chuẩn văn bản subtitle không hợp lệ.");
    // Text import can include caption URLs as literals, but it never receives
    // files, paths, provider/job handles or a browser-selected upload.
    const safety = subtitleStudioSecretSafetyError(text);
    if (safety) throw new Error(safety);
    return { format, content: text };
  }
  async function copySubtitleStudioText(value) {
    const text = String(value || "");
    if (!text || text.length > 100000) throw new Error("Máy chủ chưa trả văn bản subtitle hợp lệ để sao chép.");
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const field = document.createElement("textarea");
    field.value = text;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.appendChild(field);
    field.select();
    const copied = document.execCommand("copy");
    field.remove();
    if (!copied) throw new Error("Trình duyệt chưa cho phép sao chép văn bản subtitle.");
  }
  function subtitleStudioBoundaryIsSafe(value) {
    const source = value && typeof value === "object" ? value : {};
    const boundary = source.boundary && typeof source.boundary === "object" ? source.boundary : source;
    return Boolean(
      boundary.execution === "authoring_only"
      && boundary.provider_called === false
      && boundary.output_created === false
      && boundary.asr_called === false
      && boundary.tts_called === false
      && boundary.dubbing_called === false
      && boundary.translation_called === false
    );
  }

  async function downloadPromptLibraryExport() {
    const context = base();
    const csrfToken = context.session && context.session.csrfToken ? String(context.session.csrfToken) : "";
    if (!csrfToken) throw new Error("Phiên signed session đã hết hạn; hãy đăng nhập lại trước khi export.");
    const headers = new Headers({ Accept: "application/json", "X-Request-ID": randomKey("web") });
    headers.set("X-CSRF-Token", csrfToken);
    const response = await fetch(`${API}/prompt-library/export`, { method: "POST", credentials: "same-origin", headers });
    if (!response.ok) {
      let payload = {};
      try { payload = await response.json(); } catch (_) { /* generic error below */ }
      const error = new Error(payload.message || "Export Prompt Library chưa được máy chủ xác nhận.");
      error.payload = payload;
      error.status = response.status;
      throw error;
    }
    const blob = await response.blob();
    if (!blob.size) throw new Error("Máy chủ chưa trả JSON export hợp lệ.");
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = "toan-aas-prompt-library.json";
    anchor.hidden = true;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1500);
    return { message: "Đã chuẩn bị JSON export riêng tư từ Prompt Library." };
  }

  function memoryReminderPayload(fields) {
    const title = String(fields.title || "").replace(/\s+/g, " ").trim();
    const body = String(fields.body || "").trim();
    const dueAt = String(fields.due_at || "").trim();
    const timezone = String(fields.timezone || "Asia/Ho_Chi_Minh").trim();
    const repeatRule = String(fields.repeat_rule || "none").trim().toLowerCase();
    const noteId = String(fields.note_id || "").trim();
    if (title.length < 3 || title.length > 160) throw new Error("Tiêu đề reminder cần từ 3 đến 160 ký tự.");
    if (body.length > 2000) throw new Error("Ghi chú reminder tối đa 2.000 ký tự.");
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/.test(dueAt)) throw new Error("Hãy chọn một thời điểm reminder hợp lệ.");
    if (!["Asia/Ho_Chi_Minh", "UTC"].includes(timezone)) throw new Error("Múi giờ reminder không hợp lệ.");
    if (!["none", "daily", "weekly", "monthly", "yearly"].includes(repeatRule)) throw new Error("Chu kỳ lặp reminder không hợp lệ.");
    if (noteId && !validMemoryId(noteId)) throw new Error("Ghi chú liên kết không hợp lệ.");
    return { note_id: noteId || null, title, body, due_at: dueAt, timezone, repeat_rule: repeatRule };
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
    const pdfToImagesEnabled = Boolean(status.flags && status.flags.pdf_to_images_enabled === true);
    const pdfToWordEnabled = Boolean(status.flags && status.flags.pdf_to_word_enabled === true);
    const imageOperationsEnabled = Boolean(status.flags && status.flags.image_operations_enabled === true);
    const imageResizeEnabled = Boolean(status.flags && status.flags.image_resize_enabled === true);
    const imageEnhanceEnabled = Boolean(status.flags && status.flags.image_enhance_enabled === true);
    // Memory Center is a signed-account Web-native capability. Its flag does
    // not imply Bot bridge, Telegram, wallet, payment or provider readiness.
    const memoryCenterEnabled = Boolean(status.flags && status.flags.memory_center_enabled === true);
    // Prompt Library is another signed-account Web-native boundary. It has no
    // dependency on Telegram identity, a Core Bridge, provider, jobs, Xu or
    // payment readiness.
    const promptLibraryEnabled = Boolean(status.flags && status.flags.prompt_library_enabled === true);
    // Audio Library & Briefing is a distinct Web-owned metadata/Asset Vault
    // relation.  Its flag never represents a music provider, AI generation,
    // external preview, Bot job, wallet, Xu or payment capability.
    const mediaWorkspaceEnabled = Boolean(status.flags && status.flags.music_media_workspace_enabled === true);
    // Content Studio is a signed-account authoring workspace only. Its flag
    // deliberately has no Bot bridge, Telegram, provider, payment, Xu, job
    // or publishing implication.
    const contentStudioEnabled = Boolean(status.flags && status.flags.content_studio_enabled === true);
    // Voice Studio is an independently owned, metadata-and-script authoring
    // workspace. It does not imply access to a Bot voice profile, TTS, clone,
    // preview, audio delivery, provider, job, wallet, Xu or payment flow.
    const voiceStudioEnabled = Boolean(status.flags && status.flags.voice_studio_enabled === true);
    // Video Production Studio is another signed-account Web-native boundary.
    // Its flag permits planning/review records only; it never means media
    // execution, rendering, output or delivery is available.
    const videoStudioEnabled = Boolean(status.flags && status.flags.video_studio_enabled === true);
    // Subtitle Studio is a signed-account, text-only authoring workspace. Its
    // feature flag never represents ASR, translation, TTS, dubbing, upload,
    // file export, provider, job, wallet, Xu or payment availability.
    const subtitleStudioEnabled = Boolean(status.flags && status.flags.subtitle_studio_enabled === true);
    // Image Creative Studio is deliberately fail-closed by its own feature
    // flag.  A true flag permits private art-direction records only; it never
    // indicates an image provider, generator, preview, job, wallet or payment
    // capability is available.
    const imageStudioEnabled = Boolean(status.flags && status.flags.image_studio_enabled === true);
    // Document & PDF Workspace is a harmless authoring-only signed-account
    // surface. Its flag never enables document operations, OCR, translation,
    // a provider, Bot bridge, job, wallet, payment or delivery.
    const documentWorkspaceEnabled = Boolean(status.flags && status.flags.document_workspace_enabled === true);
    // AI Chat Workspace only unlocks signed Web-owned authoring records. It
    // never enables a model, assistant reply, provider stream, Bot mode,
    // wallet, payment, job, output or delivery path.
    const chatWorkspaceEnabled = Boolean(status.flags && status.flags.chat_workspace_enabled === true);
    // Analytics Workspace owns only manual observations entered by the
    // signed Web account.  Its flag never means that a platform connection,
    // Bot report, provider analytics, AI insight, revenue, wallet, payment,
    // job, publish action or export is available.
    const analyticsWorkspaceEnabled = Boolean(status.flags && status.flags.analytics_workspace_enabled === true);
    // Support Desk has the same independence property: a Telegram link or a
    // Core Bridge may be absent while a signed Web account can still use its
    // own case store.  Its server route remains the real feature gate.
    const supportDeskEnabled = Boolean(status.flags && status.flags.support_desk_enabled === true);
    // This native page must never display the static catalog's `ready` badge
    // while its server-side execution gate is intentionally off.
    const nativeDocumentPageStates = {
      "/documents/image-to-pdf": account && assetVaultEnabled && documentOperationsEnabled && imageToPdfEnabled ? "ready" : "guarded",
      "/documents/pdf-to-images": account && assetVaultEnabled && documentOperationsEnabled && pdfToImagesEnabled ? "ready" : "guarded",
      "/documents/pdf-to-word": account && assetVaultEnabled && documentOperationsEnabled && pdfToWordEnabled ? "ready" : "guarded"
    };
    const nativeImagePageStates = {
      // The private source/history reads still need to complete before a
      // server-enabled native page can truthfully show a ready badge.
      "/image/resize": account && assetVaultEnabled && imageOperationsEnabled && imageResizeEnabled ? "processing" : "guarded",
      "/image/edit": account && assetVaultEnabled && imageOperationsEnabled && imageEnhanceEnabled ? "processing" : "guarded"
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
      "document-operation-pdf-to-images": Boolean(account && me.csrf_token && assetVaultEnabled && documentOperationsEnabled && pdfToImagesEnabled),
      "document-operation-pdf-to-word": Boolean(account && me.csrf_token && assetVaultEnabled && documentOperationsEnabled && pdfToWordEnabled),
      "document-operation-refresh": Boolean(account && assetVaultEnabled && documentOperationsEnabled),
      // Resize & Aspect Studio is a separate Web-native image contract. It
      // needs no Telegram link/Core Bridge/provider/wallet, but remains
      // guarded until its own isolated storage and narrow decoder flag exist.
      "image-operation-view": Boolean(account && assetVaultEnabled && imageOperationsEnabled),
      "image-operation-resize": Boolean(account && me.csrf_token && assetVaultEnabled && imageOperationsEnabled && imageResizeEnabled),
      "image-operation-refresh": Boolean(account && assetVaultEnabled && imageOperationsEnabled),
      "image-operation-enhance": Boolean(account && me.csrf_token && assetVaultEnabled && imageOperationsEnabled && imageEnhanceEnabled),
      "image-enhance-refresh": Boolean(account && assetVaultEnabled && imageOperationsEnabled),
      // Notes and reminders are private browser-account data, protected by
      // server-side session/CSRF/ownership/revision checks. They must remain
      // usable without a Telegram link and never announce external delivery.
      "memory-view": Boolean(account && memoryCenterEnabled),
      "memory-refresh": Boolean(account && memoryCenterEnabled),
      "memory-note-create": Boolean(account && me.csrf_token && memoryCenterEnabled),
      "memory-note-update": Boolean(account && me.csrf_token && memoryCenterEnabled),
      "memory-note-archive": Boolean(account && me.csrf_token && memoryCenterEnabled),
      "memory-note-restore": Boolean(account && me.csrf_token && memoryCenterEnabled),
      "memory-note-restore-version": Boolean(account && me.csrf_token && memoryCenterEnabled),
      "memory-reminder-create": Boolean(account && me.csrf_token && memoryCenterEnabled),
      "memory-reminder-update": Boolean(account && me.csrf_token && memoryCenterEnabled),
      "memory-reminder-complete": Boolean(account && me.csrf_token && memoryCenterEnabled),
      "memory-reminder-pause": Boolean(account && me.csrf_token && memoryCenterEnabled),
      "memory-reminder-resume": Boolean(account && me.csrf_token && memoryCenterEnabled),
      "memory-reminder-cancel": Boolean(account && me.csrf_token && memoryCenterEnabled),
      "prompt-library-view": Boolean(account && promptLibraryEnabled),
      "prompt-library-refresh": Boolean(account && promptLibraryEnabled),
      "prompt-library-create": Boolean(account && me.csrf_token && promptLibraryEnabled),
      "prompt-library-update": Boolean(account && me.csrf_token && promptLibraryEnabled),
      "prompt-library-archive": Boolean(account && me.csrf_token && promptLibraryEnabled),
      "prompt-library-restore": Boolean(account && me.csrf_token && promptLibraryEnabled),
      "prompt-library-purge": Boolean(account && me.csrf_token && promptLibraryEnabled),
      "prompt-library-duplicate": Boolean(account && me.csrf_token && promptLibraryEnabled),
      "prompt-library-restore-version": Boolean(account && me.csrf_token && promptLibraryEnabled),
      "prompt-library-preview": Boolean(account && me.csrf_token && promptLibraryEnabled),
      "prompt-library-import": Boolean(account && me.csrf_token && promptLibraryEnabled),
      "prompt-library-export": Boolean(account && me.csrf_token && promptLibraryEnabled),
      "media-workspace-view": Boolean(account && mediaWorkspaceEnabled),
      "media-workspace-refresh": Boolean(account && mediaWorkspaceEnabled),
      "media-workspace-create": Boolean(account && me.csrf_token && mediaWorkspaceEnabled),
      "media-workspace-update": Boolean(account && me.csrf_token && mediaWorkspaceEnabled),
      "media-workspace-archive": Boolean(account && me.csrf_token && mediaWorkspaceEnabled),
      "media-workspace-restore": Boolean(account && me.csrf_token && mediaWorkspaceEnabled),
      "media-workspace-duplicate": Boolean(account && me.csrf_token && mediaWorkspaceEnabled),
      "media-workspace-restore-version": Boolean(account && me.csrf_token && mediaWorkspaceEnabled),
      "media-workspace-compose": Boolean(account && me.csrf_token && mediaWorkspaceEnabled),
      "media-workspace-item-attach": Boolean(account && me.csrf_token && mediaWorkspaceEnabled),
      "media-workspace-item-update": Boolean(account && me.csrf_token && mediaWorkspaceEnabled),
      "media-workspace-item-detach": Boolean(account && me.csrf_token && mediaWorkspaceEnabled),
      "content-studio-view": Boolean(account && contentStudioEnabled),
      "content-studio-refresh": Boolean(account && contentStudioEnabled),
      "content-studio-create": Boolean(account && me.csrf_token && contentStudioEnabled),
      "content-studio-update": Boolean(account && me.csrf_token && contentStudioEnabled),
      "content-studio-archive": Boolean(account && me.csrf_token && contentStudioEnabled),
      "content-studio-restore": Boolean(account && me.csrf_token && contentStudioEnabled),
      "content-studio-duplicate": Boolean(account && me.csrf_token && contentStudioEnabled),
      "content-studio-restore-version": Boolean(account && me.csrf_token && contentStudioEnabled),
      "content-studio-compose": Boolean(account && me.csrf_token && contentStudioEnabled),
      "content-studio-variant-create": Boolean(account && me.csrf_token && contentStudioEnabled),
      "content-studio-variant-update": Boolean(account && me.csrf_token && contentStudioEnabled),
      "content-studio-variant-archive": Boolean(account && me.csrf_token && contentStudioEnabled),
      "content-studio-variant-restore": Boolean(account && me.csrf_token && contentStudioEnabled),
      "content-studio-variant-select": Boolean(account && me.csrf_token && contentStudioEnabled),
      "voice-studio-view": Boolean(account && voiceStudioEnabled),
      "voice-studio-refresh": Boolean(account && voiceStudioEnabled),
      "voice-vault-create": Boolean(account && me.csrf_token && voiceStudioEnabled),
      "voice-vault-update": Boolean(account && me.csrf_token && voiceStudioEnabled),
      "voice-vault-archive": Boolean(account && me.csrf_token && voiceStudioEnabled),
      "voice-vault-restore": Boolean(account && me.csrf_token && voiceStudioEnabled),
      "voice-vault-duplicate": Boolean(account && me.csrf_token && voiceStudioEnabled),
      "voice-vault-restore-version": Boolean(account && me.csrf_token && voiceStudioEnabled),
      "voice-vault-compose": Boolean(account && me.csrf_token && voiceStudioEnabled),
      "voice-script-create": Boolean(account && me.csrf_token && voiceStudioEnabled),
      "voice-script-update": Boolean(account && me.csrf_token && voiceStudioEnabled),
      "voice-script-archive": Boolean(account && me.csrf_token && voiceStudioEnabled),
      "voice-script-restore": Boolean(account && me.csrf_token && voiceStudioEnabled),
      "voice-script-duplicate": Boolean(account && me.csrf_token && voiceStudioEnabled),
      "voice-script-restore-version": Boolean(account && me.csrf_token && voiceStudioEnabled),
      "voice-script-cue-sheet": Boolean(account && voiceStudioEnabled),
      "video-studio-view": Boolean(account && videoStudioEnabled),
      "video-studio-refresh": Boolean(account && videoStudioEnabled),
      "video-plan-create": Boolean(account && me.csrf_token && videoStudioEnabled),
      "video-plan-update": Boolean(account && me.csrf_token && videoStudioEnabled),
      "video-plan-lifecycle": Boolean(account && me.csrf_token && videoStudioEnabled),
      "video-plan-restore-version": Boolean(account && me.csrf_token && videoStudioEnabled),
      "video-scene-create": Boolean(account && me.csrf_token && videoStudioEnabled),
      "video-scene-update": Boolean(account && me.csrf_token && videoStudioEnabled),
      "video-scene-archive": Boolean(account && me.csrf_token && videoStudioEnabled),
      "video-scene-restore": Boolean(account && me.csrf_token && videoStudioEnabled),
      "video-scene-restore-version": Boolean(account && me.csrf_token && videoStudioEnabled),
      "video-scene-reorder": Boolean(account && me.csrf_token && videoStudioEnabled),
      "subtitle-studio-view": Boolean(account && subtitleStudioEnabled),
      "subtitle-studio-refresh": Boolean(account && subtitleStudioEnabled),
      "subtitle-project-create": Boolean(account && me.csrf_token && subtitleStudioEnabled),
      "subtitle-project-update": Boolean(account && me.csrf_token && subtitleStudioEnabled),
      "subtitle-project-lifecycle": Boolean(account && me.csrf_token && subtitleStudioEnabled),
      "subtitle-project-restore-version": Boolean(account && me.csrf_token && subtitleStudioEnabled),
      "subtitle-cue-create": Boolean(account && me.csrf_token && subtitleStudioEnabled),
      "subtitle-cue-import": Boolean(account && me.csrf_token && subtitleStudioEnabled),
      "subtitle-cue-update": Boolean(account && me.csrf_token && subtitleStudioEnabled),
      "subtitle-cue-archive": Boolean(account && me.csrf_token && subtitleStudioEnabled),
      "subtitle-cue-restore": Boolean(account && me.csrf_token && subtitleStudioEnabled),
      "subtitle-cue-restore-version": Boolean(account && me.csrf_token && subtitleStudioEnabled),
      "subtitle-cue-reorder": Boolean(account && me.csrf_token && subtitleStudioEnabled),
      "subtitle-text-export": Boolean(account && subtitleStudioEnabled),
      "image-studio-view": Boolean(account && imageStudioEnabled),
      "image-studio-refresh": Boolean(account && imageStudioEnabled),
      "image-artboard-create": Boolean(account && me.csrf_token && imageStudioEnabled),
      "image-artboard-update": Boolean(account && me.csrf_token && imageStudioEnabled),
      "image-artboard-lifecycle": Boolean(account && me.csrf_token && imageStudioEnabled),
      "image-artboard-restore-version": Boolean(account && me.csrf_token && imageStudioEnabled),
      "image-direction-create": Boolean(account && me.csrf_token && imageStudioEnabled),
      "image-direction-update": Boolean(account && me.csrf_token && imageStudioEnabled),
      "image-direction-archive": Boolean(account && me.csrf_token && imageStudioEnabled),
      "image-direction-restore": Boolean(account && me.csrf_token && imageStudioEnabled),
      "image-direction-restore-version": Boolean(account && me.csrf_token && imageStudioEnabled),
      "document-workspace-view": Boolean(account && documentWorkspaceEnabled),
      "document-workspace-refresh": Boolean(account && documentWorkspaceEnabled),
      "document-workspace-create": Boolean(account && me.csrf_token && documentWorkspaceEnabled),
      "document-workspace-update": Boolean(account && me.csrf_token && documentWorkspaceEnabled),
      "document-workspace-lifecycle": Boolean(account && me.csrf_token && documentWorkspaceEnabled),
      "document-workspace-restore-version": Boolean(account && me.csrf_token && documentWorkspaceEnabled),
      "document-plan-create": Boolean(account && me.csrf_token && documentWorkspaceEnabled),
      "document-plan-update": Boolean(account && me.csrf_token && documentWorkspaceEnabled),
      "document-plan-archive": Boolean(account && me.csrf_token && documentWorkspaceEnabled),
      "document-plan-restore": Boolean(account && me.csrf_token && documentWorkspaceEnabled),
      "document-plan-restore-version": Boolean(account && me.csrf_token && documentWorkspaceEnabled),
      "document-plan-reorder": Boolean(account && me.csrf_token && documentWorkspaceEnabled),
      "chat-workspace-view": Boolean(account && chatWorkspaceEnabled),
      "chat-workspace-refresh": Boolean(account && chatWorkspaceEnabled),
      "chat-workspace-filter": Boolean(account && chatWorkspaceEnabled),
      "chat-workspace-page": Boolean(account && chatWorkspaceEnabled),
      "chat-thread-create": Boolean(account && me.csrf_token && chatWorkspaceEnabled),
      "chat-thread-update": Boolean(account && me.csrf_token && chatWorkspaceEnabled),
      "chat-thread-lifecycle": Boolean(account && me.csrf_token && chatWorkspaceEnabled),
      "chat-thread-restore-version": Boolean(account && me.csrf_token && chatWorkspaceEnabled),
      "chat-context-create": Boolean(account && me.csrf_token && chatWorkspaceEnabled),
      "chat-context-update": Boolean(account && me.csrf_token && chatWorkspaceEnabled),
      "chat-context-state": Boolean(account && me.csrf_token && chatWorkspaceEnabled),
      "chat-turn-create": Boolean(account && me.csrf_token && chatWorkspaceEnabled),
      "chat-turn-state": Boolean(account && me.csrf_token && chatWorkspaceEnabled),
      "analytics-workspace-view": Boolean(account && analyticsWorkspaceEnabled),
      "analytics-workspace-refresh": Boolean(account && analyticsWorkspaceEnabled),
      "analytics-workspace-filter": Boolean(account && analyticsWorkspaceEnabled),
      "analytics-workspace-page": Boolean(account && analyticsWorkspaceEnabled),
      "analytics-report-create": Boolean(account && me.csrf_token && analyticsWorkspaceEnabled),
      "analytics-report-update": Boolean(account && me.csrf_token && analyticsWorkspaceEnabled),
      "analytics-report-lifecycle": Boolean(account && me.csrf_token && analyticsWorkspaceEnabled),
      "analytics-report-restore-version": Boolean(account && me.csrf_token && analyticsWorkspaceEnabled),
      "analytics-metric-create": Boolean(account && me.csrf_token && analyticsWorkspaceEnabled),
      "analytics-metric-update": Boolean(account && me.csrf_token && analyticsWorkspaceEnabled),
      "analytics-metric-state": Boolean(account && me.csrf_token && analyticsWorkspaceEnabled),
      "analytics-snapshot-create": Boolean(account && me.csrf_token && analyticsWorkspaceEnabled),
      "analytics-snapshot-update": Boolean(account && me.csrf_token && analyticsWorkspaceEnabled),
      "analytics-snapshot-state": Boolean(account && me.csrf_token && analyticsWorkspaceEnabled),
      "analytics-finding-create": Boolean(account && me.csrf_token && analyticsWorkspaceEnabled),
      "analytics-finding-update": Boolean(account && me.csrf_token && analyticsWorkspaceEnabled),
      "analytics-finding-state": Boolean(account && me.csrf_token && analyticsWorkspaceEnabled),
      // Native support reads/writes are server-authenticated Web operations.
      // Admin support capability intentionally does not trust `account.role`
      // here: the support endpoints check protected role_cache themselves.
      "support-case-view": Boolean(account && supportDeskEnabled),
      "support-case-refresh": Boolean(account && supportDeskEnabled),
      "support-case-create": Boolean(account && me.csrf_token && supportDeskEnabled),
      "support-case-reply": Boolean(account && me.csrf_token && supportDeskEnabled),
      "support-case-transition": Boolean(account && me.csrf_token && supportDeskEnabled),
      "support-admin-case-view": Boolean(account && supportDeskEnabled),
      "support-admin-case-refresh": Boolean(account && supportDeskEnabled),
      "support-admin-case-write": Boolean(account && me.csrf_token && supportDeskEnabled),
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
      pdfToImagesEnabled,
      pdfToWordEnabled,
      imageOperationsEnabled,
      imageResizeEnabled,
      imageEnhanceEnabled,
      memoryCenterEnabled,
      promptLibraryEnabled,
      mediaWorkspaceEnabled,
      contentStudioEnabled,
      voiceStudioEnabled,
      videoStudioEnabled,
      subtitleStudioEnabled,
      imageStudioEnabled,
      documentWorkspaceEnabled,
      chatWorkspaceEnabled,
      analyticsWorkspaceEnabled,
      supportDeskEnabled,
      // Clear every account-scoped projection while hydration starts. A failed
      // request must never render the previous account's note/reminder data.
      memorySummary: {},
      memoryNotes: [],
      memoryReminders: [],
      memoryEvents: [],
      memoryNoteDetail: {},
      memoryNoteFilter: { q: "", priority: "", state: "all" },
      memoryReadState: account && memoryCenterEnabled ? "loading" : "guarded",
      // Clear every Prompt Library projection before an account-scoped read.
      // A signed account change or a failed API request must never show a
      // previous owner's recipe, preview, version metadata or event stream.
      promptLibrarySummary: {},
      promptTemplates: [],
      promptTemplateDetail: {},
      promptTemplatePreview: {},
      promptLibraryEvents: [],
      promptLibraryFilter: { q: "", category: "", platform: "", product_context: "", tag: "", state: "all" },
      promptLibraryReadState: account && promptLibraryEnabled ? "loading" : "guarded",
      // Always clear every Audio Workspace projection before the signed
      // owner-scoped read starts.  A session change/failure must never leave
      // a prior user's brief, Asset Vault metadata or audit labels visible.
      mediaWorkspaceSummary: {},
      mediaCollections: [],
      mediaCollectionDetail: {},
      mediaComposer: {},
      mediaAudioAssets: [],
      mediaWorkspaceEvents: [],
      mediaWorkspacePolicy: {},
      mediaWorkspaceFilter: { q: "", tag: "", prompt_mode: "", state: "all" },
      mediaWorkspaceReadState: account && mediaWorkspaceEnabled ? "loading" : "guarded",
      // Fail closed across account/session transitions. Content Studio never
      // uses a prior owner's projection or generic canonical feature data.
      contentStudioSummary: {},
      contentBriefs: [],
      contentBriefDetail: {},
      contentVariantHistory: {},
      contentStudioComposer: {},
      contentStudioReferences: {},
      contentStudioEvents: [],
      contentStudioPolicy: {},
      contentStudioFilter: { q: "", tag: "", content_kind: "", state: "all" },
      contentStudioReadState: account && contentStudioEnabled ? "loading" : "guarded",
      // Voice Studio is cleared independently before every signed hydration.
      // No prior account's consent assertion, script, cue estimate, version,
      // or reference metadata may survive a session change/read failure.
      voiceStudioSummary: {},
      voiceVaults: [],
      voiceVaultDetail: {},
      voiceStudioReferences: {},
      voiceStudioEvents: [],
      voiceStudioPolicy: {},
      voiceCueSheet: {},
      voiceStudioFilter: { q: "", tag: "", state: "all" },
      voiceStudioReadState: account && voiceStudioEnabled ? "loading" : "guarded",
      // Clear every Video Production Studio projection before a signed read.
      // A failed request or account switch must never leave a prior owner's
      // brief, scene, runtime estimate or audit metadata on screen.
      videoStudioSummary: {},
      videoPlans: [],
      videoPlanDetail: {},
      videoPlanEstimate: {},
      videoStudioReferences: {},
      videoStudioEvents: [],
      videoStudioReadState: account && videoStudioEnabled ? "loading" : "guarded",
      // Transcript/cue projections are owner-scoped.  Always clear them
      // during hydration so a failed signed request cannot expose a prior
      // account's caption text, language draft or version metadata.
      subtitleStudioSummary: {},
      subtitleProjects: [],
      subtitleProjectDetail: {},
      subtitleProjectEstimate: {},
      subtitleStudioReferences: {},
      subtitleStudioEvents: [],
      subtitleStudioReadState: account && subtitleStudioEnabled ? "loading" : "guarded",
      // Explicitly clear owner-scoped creative metadata during every session
      // refresh. A disabled flag or failed request must not leave a prior
      // artboard, asset reference, prompt or history visible in the browser.
      imageStudioSummary: {},
      imageArtboards: [],
      imageArtboardDetail: {},
      imageArtboardEstimate: {},
      imageStudioReferences: {},
      imageStudioEvents: [],
      imageStudioPolicy: {},
      imageStudioReadState: account && imageStudioEnabled ? "loading" : "guarded",
      // Document Workspace data is owner-scoped. Clear it before every
      // session refresh so a failed read can never reveal another account's
      // brief, plan, Asset Vault metadata or version/event history.
      documentWorkspaceSummary: {},
      documentWorkspaces: [],
      documentWorkspaceDetail: {},
      documentWorkspaceEstimate: {},
      documentWorkspaceReferences: {},
      documentWorkspaceEvents: [],
      documentWorkspacePolicy: {},
      documentWorkspaceReadState: account && documentWorkspaceEnabled ? "loading" : "guarded",
      // Chat threads can contain private authoring text. Clear every signed
      // projection first so a session change or failed read cannot reveal a
      // prior account's context card, turn or version history.
      chatWorkspaceSummary: {},
      chatThreads: [],
      chatThreadDetail: {},
      chatWorkspaceReferences: {},
      chatWorkspaceEvents: [],
      chatWorkspacePolicy: {},
      chatWorkspaceListing: { state: "all", q: "", pagination: { total: 0, limit: 50, offset: 0, returned: 0, has_more: false, next_offset: null, previous_offset: null } },
      chatWorkspaceReadState: account && chatWorkspaceEnabled ? "loading" : "guarded",
      // Manual Analytics reports can include private internal observation
      // notes. Clear every owner-scoped projection before a signed read so a
      // failed request or account switch cannot reveal a previous account's
      // report, snapshot, finding, comparison or history.
      analyticsWorkspaceSummary: {},
      analyticsReports: [],
      analyticsReportDetail: {},
      analyticsWorkspaceReferences: {},
      analyticsWorkspacePolicy: {},
      analyticsWorkspaceListing: { state: "all", q: "", pagination: { total: 0, limit: 50, offset: 0, returned: 0, has_more: false, next_offset: null, previous_offset: null } },
      analyticsWorkspaceReadState: account && analyticsWorkspaceEnabled ? "loading" : "guarded",
      // Clear Support Desk projections before every authenticated hydration.
      // A signed account switch or failed read must never leave a prior
      // customer's case/thread/role visible in the browser.
      supportSummary: {},
      supportCases: [],
      supportEvents: [],
      supportCaseDetail: {},
      supportCaseFilter: { q: "", state: "all", category: "" },
      supportReadState: account && supportDeskEnabled ? "loading" : "guarded",
      supportAdminSummary: {},
      supportAdminCases: [],
      supportAdminCaseDetail: {},
      supportAdminCaseFilter: { q: "", state: "all", category: "" },
      supportAdminReadState: account && supportDeskEnabled ? "loading" : "guarded",
      // These owner-scoped reads start as loading on every signed hydration.
      // A native operation form may only become actionable after both the
      // Asset Vault source projection and its own history projection return.
      assetVaultReadState: account && assetVaultEnabled ? "loading" : "guarded",
      imageOperationsReadState: account && assetVaultEnabled && imageOperationsEnabled ? "loading" : "guarded",
      imageEnhanceOperationsReadState: account && assetVaultEnabled && imageOperationsEnabled ? "loading" : "guarded",
      documentOperations: account && Array.isArray(context.documentOperations) ? context.documentOperations : [],
      imageOperations: account && Array.isArray(context.imageOperations) ? context.imageOperations : [],
      // Do not retain a previous signed projection while the new owner-scoped
      // Enhance history is loading. The UI deliberately renders no form or
      // artifact until both private reads settle.
      imageEnhanceOperations: [],
      workspaceDraftFeatures: webWorkspaceDraftFeatures,
      pwaEnabled: Boolean(status.flags && status.flags.pwa_enabled),
      capabilities,
      pageStates: {
        ...featurePageStates(catalog, {}, webFeatureExecutionFeatures, webWorkspaceDraftFeatures, Boolean(account && me.csrf_token)),
        ...nativeDocumentPageStates,
        ...nativeImagePageStates,
        "/notes": account && memoryCenterEnabled ? "processing" : "guarded",
        "/reminders": account && memoryCenterEnabled ? "processing" : "guarded",
        "/prompt-library": account && promptLibraryEnabled ? "processing" : "guarded",
        "/prompt-library/new": account && promptLibraryEnabled ? "processing" : "guarded",
        "/media-workspace": account && mediaWorkspaceEnabled ? "processing" : "guarded",
        "/media-workspace/new": account && mediaWorkspaceEnabled ? "processing" : "guarded",
        "/content-studio": account && contentStudioEnabled ? "processing" : "guarded",
        "/content-studio/new": account && contentStudioEnabled ? "processing" : "guarded",
        "/voice-studio": account && voiceStudioEnabled ? "processing" : "guarded",
        "/voice-studio/new": account && voiceStudioEnabled ? "processing" : "guarded",
        "/video-studio": account && videoStudioEnabled ? "processing" : "guarded",
        "/video-studio/new": account && videoStudioEnabled ? "processing" : "guarded",
        "/subtitle-studio": account && subtitleStudioEnabled ? "processing" : "guarded",
        "/subtitle-studio/new": account && subtitleStudioEnabled ? "processing" : "guarded",
        "/image-studio": account && imageStudioEnabled ? "processing" : "guarded",
        "/image-studio/new": account && imageStudioEnabled ? "processing" : "guarded",
        "/document-workspace": account && documentWorkspaceEnabled ? "processing" : "guarded",
        "/document-workspace/new": account && documentWorkspaceEnabled ? "processing" : "guarded",
        "/chat": account && chatWorkspaceEnabled ? "processing" : "guarded",
        "/chat/new": account && chatWorkspaceEnabled ? "processing" : "guarded",
        "/analytics": account && analyticsWorkspaceEnabled ? "processing" : "guarded",
        "/analytics/new": account && analyticsWorkspaceEnabled ? "processing" : "guarded",
        "/support": account && supportDeskEnabled ? "processing" : "guarded",
        "/tickets": account && supportDeskEnabled ? "processing" : "guarded",
        "/admin/support": account && supportDeskEnabled ? "processing" : "guarded"
      }
    });
    if (status.flags && status.flags.pwa_enabled && "serviceWorker" in navigator) {
      navigator.serviceWorker.register("/static/portal/service-worker.js").catch(() => {});
    }
    const currentPath = (context.path || window.location.pathname).split("?")[0];
    if (account && ["/campaigns", "/calendar", "/approvals"].includes(currentPath)) await hydrateCampaignPlans();
    else if (account && campaignPlanIdFromPath(currentPath)) await hydrateCampaignPlanDetail(currentPath);
    if (account && (["/projects", "/project-packages", "/dashboard", "/media-workspace", "/media-workspace/new", "/content-studio", "/content-studio/new", "/voice-studio", "/voice-studio/new", "/video-studio", "/video-studio/new", "/subtitle-studio", "/subtitle-studio/new", "/image-studio", "/image-studio/new", "/document-workspace", "/document-workspace/new"].includes(currentPath) || isNativeMediaWorkspacePath(currentPath) || isNativeContentStudioPath(currentPath) || isNativeVoiceStudioPath(currentPath) || isNativeVideoStudioPath(currentPath) || isNativeSubtitleStudioPath(currentPath) || isNativeImageStudioPath(currentPath) || isNativeDocumentWorkspacePath(currentPath))) await hydrateProjects();
    else if (account && projectIdFromPath(currentPath)) await hydrateProjectDetail(currentPath);
    if (account && projectPackageEnabled && currentPath === "/project-packages") await hydrateProjectPackages();
    else if (account && projectPackageEnabled && projectIdFromPath(currentPath)) await hydrateProjectPackages(projectIdFromPath(currentPath));
    else if (account && currentPath === "/project-packages") merge({ projectPackages: [], pageStates: { ...(base().pageStates || {}), "/project-packages": "guarded" } });
    if (account && assetVaultEnabled && ["/asset-vault", "/dashboard", "/documents/split", "/documents/merge", "/documents/compress", "/documents/image-to-pdf", "/documents/pdf-to-images", "/documents/pdf-to-word", "/image/resize", "/image/edit"].includes(currentPath)) await hydrateAssetVault();
    else if (account && ["/asset-vault", "/image/resize", "/image/edit"].includes(currentPath)) merge({
      vaultItems: [],
      assetVaultReadState: "guarded",
      pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
    });
    if (account && assetVaultEnabled && documentOperationsEnabled && ["/documents/split", "/documents/merge", "/documents/compress", "/documents/image-to-pdf", "/documents/pdf-to-images", "/documents/pdf-to-word"].includes(currentPath)) await hydrateDocumentOperations();
    else if (account && ["/documents/split", "/documents/merge", "/documents/compress", "/documents/image-to-pdf", "/documents/pdf-to-images", "/documents/pdf-to-word"].includes(currentPath)) merge({ documentOperations: [], pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" } });
    if (account && assetVaultEnabled && imageOperationsEnabled && currentPath === "/image/resize") await hydrateImageOperations();
    else if (account && currentPath === "/image/resize") merge({
      imageOperations: [],
      imageOperationsReadState: "guarded",
      pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
    });
    if (account && assetVaultEnabled && imageOperationsEnabled && currentPath === "/image/edit") await hydrateImageEnhanceOperations();
    else if (account && currentPath === "/image/edit") merge({
      imageEnhanceOperations: [],
      imageEnhanceOperationsReadState: "guarded",
      pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
    });
    if (account && memoryCenterEnabled && ["/notes", "/reminders"].includes(currentPath)) await hydrateMemoryCenter();
    else if (account && ["/notes", "/reminders"].includes(currentPath)) merge({
      memorySummary: {}, memoryNotes: [], memoryReminders: [], memoryEvents: [], memoryNoteDetail: {}, memoryReadState: "guarded",
      pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
    });
    if (account && promptLibraryEnabled && ["/prompt-library", "/prompt-library/new"].includes(currentPath)) await hydratePromptLibrary();
    else if (account && promptLibraryEnabled && promptTemplateIdFromPath(currentPath)) await hydratePromptTemplate(promptTemplateIdFromPath(currentPath));
    else if (currentPath === "/prompt-library" || currentPath === "/prompt-library/new" || promptTemplateIdFromPath(currentPath)) {
      merge({
        promptLibrarySummary: {}, promptTemplates: [], promptTemplateDetail: {}, promptTemplatePreview: {}, promptLibraryEvents: [],
        promptLibraryReadState: "guarded", pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
      });
    }
    if (account && mediaWorkspaceEnabled && ["/media-workspace", "/media-workspace/new"].includes(currentPath)) await hydrateMediaWorkspace();
    else if (account && mediaWorkspaceEnabled && mediaWorkspaceCollectionIdFromPath(currentPath)) await hydrateMediaCollection(mediaWorkspaceCollectionIdFromPath(currentPath));
    else if (isNativeMediaWorkspacePath(currentPath)) {
      // Never retain a previous account's audio metadata or fall back to the
      // Bot music bridge when the dedicated Web feature/session is guarded.
      merge({
        mediaWorkspaceSummary: {}, mediaCollections: [], mediaCollectionDetail: {}, mediaComposer: {}, mediaAudioAssets: [],
        mediaWorkspaceEvents: [], mediaWorkspacePolicy: {}, mediaWorkspaceReadState: "guarded",
        pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
      });
    }
    if (account && contentStudioEnabled && ["/content-studio", "/content-studio/new"].includes(currentPath)) await hydrateContentStudio();
    else if (account && contentStudioEnabled && contentBriefIdFromPath(currentPath)) await hydrateContentBrief(contentBriefIdFromPath(currentPath));
    else if (isNativeContentStudioPath(currentPath)) {
      merge({
        contentStudioSummary: {}, contentBriefs: [], contentBriefDetail: {}, contentStudioComposer: {},
        contentStudioReferences: {}, contentStudioEvents: [], contentStudioPolicy: {}, contentStudioReadState: "guarded",
        pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
      });
    }
    if (account && voiceStudioEnabled && ["/voice-studio", "/voice-studio/new"].includes(currentPath)) await hydrateVoiceStudio();
    else if (account && voiceStudioEnabled && voiceVaultIdFromPath(currentPath)) await hydrateVoiceVault(voiceVaultIdFromPath(currentPath));
    else if (isNativeVoiceStudioPath(currentPath)) {
      // Never fall back to `/voice/*` Core Bridge data. Voice Studio owns
      // only its account-scoped metadata/script boundary and fails closed.
      merge({
        voiceStudioSummary: {}, voiceVaults: [], voiceVaultDetail: {}, voiceStudioReferences: {}, voiceStudioEvents: [],
        voiceStudioPolicy: {}, voiceCueSheet: {}, voiceStudioReadState: "guarded",
        pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
      });
    }
    if (account && videoStudioEnabled && ["/video-studio", "/video-studio/new"].includes(currentPath)) await hydrateVideoStudio();
    else if (account && videoStudioEnabled && videoPlanIdFromPath(currentPath)) await hydrateVideoPlan(videoPlanIdFromPath(currentPath));
    else if (isNativeVideoStudioPath(currentPath)) {
      // Never reuse legacy `/video/*` data for this signed Web-native
      // authoring space.  It holds only plan/scene metadata and fails closed.
      merge({
        videoStudioSummary: {}, videoPlans: [], videoPlanDetail: {}, videoPlanEstimate: {}, videoStudioReferences: {}, videoStudioEvents: [],
        videoStudioReadState: "guarded", pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
      });
    }
    if (account && imageStudioEnabled && ["/image-studio", "/image-studio/new"].includes(currentPath)) await hydrateImageStudio();
    else if (account && imageStudioEnabled && imageArtboardIdFromPath(currentPath)) await hydrateImageArtboard(imageArtboardIdFromPath(currentPath));
    else if (isNativeImageStudioPath(currentPath)) {
      // Never use legacy `/image/*` operation history or an untrusted browser
      // cache as a substitute for a server-enabled, owner-scoped artboard.
      merge({
        imageStudioSummary: {}, imageArtboards: [], imageArtboardDetail: {}, imageArtboardEstimate: {}, imageStudioReferences: {}, imageStudioEvents: [], imageStudioPolicy: {},
        imageStudioReadState: "guarded", pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
      });
    }
    if (account && documentWorkspaceEnabled && ["/document-workspace", "/document-workspace/new"].includes(currentPath)) await hydrateDocumentWorkspace();
    else if (account && documentWorkspaceEnabled && documentWorkspaceIdFromPath(currentPath)) await hydrateDocumentWorkspaceDetail(documentWorkspaceIdFromPath(currentPath));
    else if (isNativeDocumentWorkspacePath(currentPath)) {
      // Never fall back to document-operation records, local form caches or a
      // prior account projection when the dedicated native route is guarded.
      merge({
        documentWorkspaceSummary: {}, documentWorkspaces: [], documentWorkspaceDetail: {}, documentWorkspaceEstimate: {},
        documentWorkspaceReferences: {}, documentWorkspaceEvents: [], documentWorkspacePolicy: {},
        documentWorkspaceReadState: "guarded", pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
      });
    }
    if (account && chatWorkspaceEnabled && ["/chat", "/chat/new"].includes(currentPath)) await hydrateChatWorkspace();
    else if (account && chatWorkspaceEnabled && chatThreadIdFromPath(currentPath)) await hydrateChatThread(chatThreadIdFromPath(currentPath));
    else if (isNativeChatWorkspacePath(currentPath)) {
      // Never fall back to the old generic `/chat` feature estimate, Bot
      // transcript or a browser draft when this native route is guarded.
      merge({
        chatWorkspaceSummary: {}, chatThreads: [], chatThreadDetail: {}, chatWorkspaceReferences: {}, chatWorkspaceEvents: [], chatWorkspacePolicy: {}, chatWorkspaceListing: { state: "all", q: "", pagination: { total: 0, limit: 50, offset: 0, returned: 0, has_more: false, next_offset: null, previous_offset: null } },
        chatWorkspaceReadState: "guarded", pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
      });
    }
    if (account && analyticsWorkspaceEnabled && ["/analytics", "/analytics/new"].includes(currentPath)) await hydrateAnalyticsWorkspace();
    else if (account && analyticsWorkspaceEnabled && analyticsReportIdFromPath(currentPath)) await hydrateAnalyticsReport(analyticsReportIdFromPath(currentPath));
    else if (isNativeAnalyticsWorkspacePath(currentPath)) {
      // Never replace a guarded signed report with a Bot report, live social
      // metric, platform API result, inferred chart or browser cache.
      merge({
        analyticsWorkspaceSummary: {}, analyticsReports: [], analyticsReportDetail: {}, analyticsWorkspaceReferences: {}, analyticsWorkspacePolicy: {},
        analyticsWorkspaceListing: { state: "all", q: "", pagination: { total: 0, limit: 50, offset: 0, returned: 0, has_more: false, next_offset: null, previous_offset: null } },
        analyticsWorkspaceReadState: "guarded", pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
      });
    }
    if (account && subtitleStudioEnabled && ["/subtitle-studio", "/subtitle-studio/new"].includes(currentPath)) await hydrateSubtitleStudio();
    else if (account && subtitleStudioEnabled && subtitleProjectIdFromPath(currentPath)) await hydrateSubtitleProject(subtitleProjectIdFromPath(currentPath));
    else if (isNativeSubtitleStudioPath(currentPath)) {
      // Never fall back to legacy subtitle/translate/dubbing/ASR state.  This
      // surface owns only signed Web authoring metadata and fails closed.
      merge({
        subtitleStudioSummary: {}, subtitleProjects: [], subtitleProjectDetail: {}, subtitleProjectEstimate: {}, subtitleStudioReferences: {}, subtitleStudioEvents: [],
        subtitleStudioReadState: "guarded", pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
      });
    }
    if (account && supportDeskEnabled) {
      if (["/support", "/tickets"].includes(currentPath)) await hydrateSupportDesk();
      else if (supportCaseIdFromPath(currentPath)) await hydrateSupportCase(supportCaseIdFromPath(currentPath));
      else if (currentPath === "/admin/support") await hydrateSupportAdmin();
      else if (supportAdminCaseIdFromPath(currentPath)) await hydrateSupportAdminCase(supportAdminCaseIdFromPath(currentPath));
    } else if (isNativeSupportPath(currentPath)) {
      // Support pages never fall back to Bot tickets, generic admin data or a
      // stale browser cache when the local feature gate/session is unavailable.
      merge({
        supportSummary: {}, supportCases: [], supportEvents: [], supportCaseDetail: {}, supportReadState: "guarded",
        supportAdminSummary: {}, supportAdminCases: [], supportAdminCaseDetail: {}, supportAdminReadState: "guarded",
        pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded" }
      });
    }
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
    // Native Support Desk routes have their own narrow API boundary.  Even if
    // a Telegram/Core Bridge happens to be available, do not let the generic
    // canonical hydrator overwrite their data with `/support/tickets` or an
    // `/admin/*` bridge projection.
    if (bridgeAvailable && !isNativeSupportPath(currentPath) && !isNativeMediaWorkspacePath(currentPath) && !isNativeContentStudioPath(currentPath) && !isNativeVoiceStudioPath(currentPath) && !isNativeVideoStudioPath(currentPath) && !isNativeImageStudioPath(currentPath)) await hydrateCanonicalData();
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

  async function hydrateMemoryCenter(filterValue) {
    // These are four owner-scoped reads from one Web-native boundary.  Keep
    // them independent from `hydrateCanonicalData`: neither a Bot bridge nor
    // a Telegram link can make Memory Center data available or unavailable.
    const filter = memoryNoteFilterPayload(filterValue === undefined ? base().memoryNoteFilter : filterValue);
    try {
      const [summaryResult, notesResult, remindersResult, eventsResult] = await Promise.all([
        api("/memory/summary"),
        api(memoryNoteListPath(filter)),
        api("/memory/reminders?state=all&limit=100"),
        api("/memory/events?limit=50")
      ]);
      const notes = notesResult.data && Array.isArray(notesResult.data.items)
        ? notesResult.data.items.filter((item) => item && validMemoryId(item.id)).slice(0, 100)
        : [];
      const reminders = remindersResult.data && Array.isArray(remindersResult.data.items)
        ? remindersResult.data.items.filter((item) => item && validMemoryId(item.id)).slice(0, 100)
        : [];
      const events = eventsResult.data && Array.isArray(eventsResult.data.items)
        ? eventsResult.data.items.filter((item) => item && validMemoryId(item.id)).slice(0, 50)
        : [];
      merge({
        memorySummary: summaryResult.data && typeof summaryResult.data === "object" ? summaryResult.data : {},
        memoryNotes: notes,
        memoryReminders: reminders,
        memoryEvents: events,
        memoryReadState: "ready",
        memoryNoteFilter: filter,
        pageStates: { ...(base().pageStates || {}), "/notes": "ready", "/reminders": "ready" }
      });
      return { notes, reminders, events };
    } catch (_) {
      // Never retain stale note text, reminder body, event metadata or a
      // previously selected detail after an account-scoped read fails.
      merge({
        memorySummary: {}, memoryNotes: [], memoryReminders: [], memoryEvents: [], memoryNoteDetail: {}, memoryNoteFilter: filter, memoryReadState: "failed",
        pageStates: { ...(base().pageStates || {}), "/notes": "guarded", "/reminders": "guarded" }
      });
      return { notes: [], reminders: [], events: [] };
    }
  }

  async function hydrateMemoryNote(noteId) {
    if (!validMemoryId(noteId)) throw new Error("Mã ghi chú Memory Center không hợp lệ.");
    const result = await api(`/memory/notes/${encodeURIComponent(String(noteId))}`);
    const detail = result.data && typeof result.data === "object" ? result.data : {};
    const note = detail.note && typeof detail.note === "object" ? detail.note : null;
    if (!note || !validMemoryId(note.id) || String(note.id) !== String(noteId)) throw new Error("Ghi chú không còn khả dụng cho Web account hiện tại.");
    const versions = Array.isArray(detail.versions) ? detail.versions.filter((item) => item && Number.isInteger(Number(item.revision))).slice(0, 50) : [];
    const reminders = Array.isArray(detail.reminders) ? detail.reminders.filter((item) => item && validMemoryId(item.id)).slice(0, 20) : [];
    merge({ memoryNoteDetail: { note, versions, reminders } });
    return { note, versions, reminders };
  }

  async function hydratePromptLibrary(filterValue) {
    // Keep this owner-scoped native data boundary independent from the
    // generic canonical/bridge hydrator. A Bot link cannot unlock or replace
    // a Prompt Library response.
    const filter = promptLibraryFilterPayload(filterValue === undefined ? base().promptLibraryFilter : filterValue);
    try {
      const [summaryResult, templatesResult, eventsResult] = await Promise.all([
        api("/prompt-library/summary"),
        api(promptLibraryListPath(filter)),
        api("/prompt-library/events?limit=50")
      ]);
      const templates = templatesResult.data && Array.isArray(templatesResult.data.items)
        ? templatesResult.data.items.filter((item) => item && validPromptTemplateId(item.id)).slice(0, 100)
        : [];
      const events = eventsResult.data && Array.isArray(eventsResult.data.items)
        ? eventsResult.data.items.filter((item) => item && validPromptTemplateId(item.template_id)).slice(0, 50)
        : [];
      merge({
        promptLibrarySummary: summaryResult.data && typeof summaryResult.data === "object" ? summaryResult.data : {},
        promptTemplates: templates,
        promptLibraryEvents: events,
        promptLibraryFilter: filter,
        promptTemplatePreview: {},
        promptLibraryReadState: "ready",
        pageStates: { ...(base().pageStates || {}), "/prompt-library": "ready", "/prompt-library/new": "ready" }
      });
      return { templates, events };
    } catch (_) {
      // Do not retain a prompt excerpt, title, tag, event, detail or preview
      // from a prior account if any owner-scoped request fails.
      merge({
        promptLibrarySummary: {}, promptTemplates: [], promptTemplateDetail: {}, promptTemplatePreview: {}, promptLibraryEvents: [],
        promptLibraryFilter: filter, promptLibraryReadState: "failed",
        pageStates: { ...(base().pageStates || {}), "/prompt-library": "guarded", "/prompt-library/new": "guarded" }
      });
      return { templates: [], events: [] };
    }
  }

  async function hydratePromptTemplate(templateId) {
    if (!validPromptTemplateId(templateId)) throw new Error("Mã template Prompt Library không hợp lệ.");
    const route = `/prompt-library/${encodeURIComponent(String(templateId))}`;
    try {
      const result = await api(`/prompt-library/templates/${encodeURIComponent(String(templateId))}`);
      const detail = result.data && typeof result.data === "object" ? result.data : {};
      const template = detail.template && typeof detail.template === "object" ? detail.template : null;
      if (!template || !validPromptTemplateId(template.id) || String(template.id) !== String(templateId)) {
        throw new Error("Template Prompt Library không còn khả dụng cho Web account hiện tại.");
      }
      const versions = Array.isArray(detail.versions)
        ? detail.versions.filter((item) => item && validPromptTemplateRevision(item.revision)).slice(0, 100)
        : [];
      merge({
        promptTemplateDetail: { template, versions },
        promptTemplatePreview: {},
        promptLibraryReadState: "ready",
        pageStates: { ...(base().pageStates || {}), [route]: "read_only" }
      });
      return { template, versions };
    } catch (_) {
      merge({
        promptTemplateDetail: {}, promptTemplatePreview: {}, promptLibraryReadState: "failed",
        pageStates: { ...(base().pageStates || {}), [route]: "guarded" }
      });
      return null;
    }
  }

  async function hydrateMediaWorkspace(filterValue) {
    // This is a narrow Web-native read boundary.  It must never use the
    // legacy `/music*` paths or a generic bridge hydration as a fallback.
    const filter = mediaWorkspaceFilterPayload(filterValue === undefined ? base().mediaWorkspaceFilter : filterValue);
    try {
      const [summaryResult, policyResult, collectionsResult, eventsResult] = await Promise.all([
        api("/media-workspace/summary"),
        api("/media-workspace/policy"),
        api(mediaWorkspaceListPath(filter)),
        api("/media-workspace/events?limit=50")
      ]);
      const collections = collectionsResult.data && Array.isArray(collectionsResult.data.items)
        ? collectionsResult.data.items.filter((item) => item && validMediaCollectionId(item.id)).slice(0, 100)
        : [];
      const events = eventsResult.data && Array.isArray(eventsResult.data.items)
        ? eventsResult.data.items.filter((item) => item && validMediaCollectionId(item.collection_id)).slice(0, 50)
        : [];
      merge({
        mediaWorkspaceSummary: summaryResult.data && typeof summaryResult.data === "object" ? summaryResult.data : {},
        mediaWorkspacePolicy: policyResult.data && typeof policyResult.data === "object" ? policyResult.data : {},
        mediaCollections: collections,
        mediaWorkspaceEvents: events,
        mediaCollectionDetail: {},
        mediaComposer: {},
        mediaAudioAssets: [],
        mediaWorkspaceFilter: filter,
        mediaWorkspaceReadState: "ready",
        pageStates: { ...(base().pageStates || {}), "/media-workspace": "ready", "/media-workspace/new": "ready" }
      });
      return { collections, events };
    } catch (_) {
      // Fail closed: no stale brief/excerpt, Asset Vault name or event can
      // survive a signed read failure or a changed account session.
      merge({
        mediaWorkspaceSummary: {}, mediaWorkspacePolicy: {}, mediaCollections: [], mediaCollectionDetail: {}, mediaComposer: {},
        mediaAudioAssets: [], mediaWorkspaceEvents: [], mediaWorkspaceFilter: filter, mediaWorkspaceReadState: "failed",
        pageStates: { ...(base().pageStates || {}), "/media-workspace": "guarded", "/media-workspace/new": "guarded" }
      });
      return { collections: [], events: [] };
    }
  }

  async function hydrateMediaCollection(collectionId) {
    if (!validMediaCollectionId(collectionId)) throw new Error("Mã Audio Collection không hợp lệ.");
    const route = `/media-workspace/${encodeURIComponent(String(collectionId))}`;
    try {
      const [detailResult, policyResult, assetsResult] = await Promise.all([
        api(`/media-workspace/collections/${encodeURIComponent(String(collectionId))}`),
        api("/media-workspace/policy"),
        api("/media-workspace/audio-assets?limit=100")
      ]);
      const data = detailResult.data && typeof detailResult.data === "object" ? detailResult.data : {};
      const collection = data.collection && typeof data.collection === "object" ? data.collection : null;
      if (!collection || !validMediaCollectionId(collection.id) || String(collection.id) !== String(collectionId)) {
        throw new Error("Audio Collection không còn khả dụng cho Web account hiện tại.");
      }
      const versions = Array.isArray(data.versions)
        ? data.versions.filter((item) => item && validMediaRevision(item.revision)).slice(0, 100)
        : [];
      const items = Array.isArray(data.items)
        ? data.items.filter((item) => item && validMediaCollectionId(item.id) && validVaultAssetId(item.asset_id)).slice(0, 250)
        : [];
      const audioAssets = assetsResult.data && Array.isArray(assetsResult.data.items)
        ? assetsResult.data.items.filter((item) => item && validVaultAssetId(item.id) && item.download_available === true).slice(0, 100)
        : [];
      merge({
        mediaCollectionDetail: { collection, versions, items, item_count: Number(data.item_count || items.length), item_limit: Number(data.item_limit || 250) },
        mediaWorkspacePolicy: policyResult.data && typeof policyResult.data === "object" ? policyResult.data : {},
        mediaAudioAssets: audioAssets,
        mediaComposer: {},
        mediaWorkspaceReadState: "ready",
        pageStates: { ...(base().pageStates || {}), [route]: "read_only" }
      });
      return { collection, versions, items, audioAssets };
    } catch (_) {
      merge({
        // Fail closed: a failed detail request must not leave a previous
        // account's collection list, summary, or event projection visible.
        mediaWorkspaceSummary: {}, mediaCollections: [], mediaWorkspaceEvents: [],
        mediaCollectionDetail: {}, mediaComposer: {}, mediaAudioAssets: [], mediaWorkspacePolicy: {}, mediaWorkspaceReadState: "failed",
        pageStates: { ...(base().pageStates || {}), [route]: "guarded" }
      });
      return null;
    }
  }

  async function hydrateContentStudio(filterValue) {
    const filter = contentStudioFilterPayload(filterValue === undefined ? base().contentStudioFilter : filterValue);
    try {
      const [summaryResult, policyResult, briefsResult, eventsResult, referencesResult] = await Promise.all([
        api("/content-studio/summary"),
        api("/content-studio/policy"),
        api(contentStudioListPath(filter)),
        api("/content-studio/events?limit=50"),
        api("/content-studio/references")
      ]);
      const briefs = briefsResult.data && Array.isArray(briefsResult.data.items)
        ? briefsResult.data.items.filter((item) => item && validContentBriefId(item.id)).slice(0, 100)
        : [];
      const events = eventsResult.data && Array.isArray(eventsResult.data.items)
        ? eventsResult.data.items.filter((item) => item && validContentBriefId(item.brief_id)).slice(0, 50)
        : [];
      merge({
        contentStudioSummary: summaryResult.data && typeof summaryResult.data === "object" ? summaryResult.data : {},
        contentStudioPolicy: policyResult.data && typeof policyResult.data === "object" ? policyResult.data : {},
        contentBriefs: briefs,
        contentStudioEvents: events,
        contentStudioReferences: referencesResult.data && typeof referencesResult.data === "object" ? referencesResult.data : {},
        contentBriefDetail: {},
        contentStudioComposer: {}, contentVariantHistory: {},
        contentStudioFilter: filter,
        contentStudioReadState: "ready",
        pageStates: { ...(base().pageStates || {}), "/content-studio": "ready", "/content-studio/new": "ready" }
      });
      return { briefs, events };
    } catch (_) {
      merge({
        contentStudioSummary: {}, contentStudioPolicy: {}, contentBriefs: [], contentBriefDetail: {}, contentVariantHistory: {}, contentStudioComposer: {},
        contentStudioReferences: {}, contentStudioEvents: [], contentStudioFilter: filter, contentStudioReadState: "failed",
        pageStates: { ...(base().pageStates || {}), "/content-studio": "guarded", "/content-studio/new": "guarded" }
      });
      return { briefs: [], events: [] };
    }
  }

  async function hydrateContentBrief(briefId) {
    if (!validContentBriefId(briefId)) throw new Error("Mã Content brief không hợp lệ.");
    const route = "/content-studio/" + encodeURIComponent(String(briefId));
    try {
      const [detailResult, policyResult, referencesResult] = await Promise.all([
        api("/content-studio/briefs/" + encodeURIComponent(String(briefId))),
        api("/content-studio/policy"),
        api("/content-studio/references")
      ]);
      const data = detailResult.data && typeof detailResult.data === "object" ? detailResult.data : {};
      const brief = data.brief && typeof data.brief === "object" ? data.brief : null;
      if (!brief || !validContentBriefId(brief.id) || String(brief.id) !== String(briefId) || !validContentStudioRevision(brief.revision)) throw new Error("Content brief không còn khả dụng.");
      const variants = Array.isArray(data.variants)
        ? data.variants.filter((item) => item && validContentBriefId(item.id) && validContentStudioRevision(item.revision)).slice(0, 250)
        : [];
      const versions = Array.isArray(data.versions)
        ? data.versions.filter((item) => item && validContentStudioRevision(item.revision)).slice(0, 100)
        : [];
      const events = Array.isArray(data.events)
        ? data.events.filter((item) => item && typeof item === "object").slice(0, 50)
        : [];
      merge({
        contentBriefDetail: { brief, variants, versions, events, variant_count: Number(data.variant_count || variants.length), variant_limit: Number(data.variant_limit || 250), references: data.references && typeof data.references === "object" ? data.references : {} },
        contentVariantHistory: {},
        contentStudioPolicy: policyResult.data && typeof policyResult.data === "object" ? policyResult.data : {},
        contentStudioReferences: referencesResult.data && typeof referencesResult.data === "object" ? referencesResult.data : {},
        contentStudioComposer: {},
        contentStudioReadState: "ready",
        pageStates: { ...(base().pageStates || {}), [route]: "read_only" }
      });
      return { brief, variants, versions };
    } catch (_) {
      merge({
        contentStudioSummary: {}, contentBriefs: [], contentBriefDetail: {}, contentVariantHistory: {}, contentStudioComposer: {},
        contentStudioReferences: {}, contentStudioEvents: [], contentStudioPolicy: {}, contentStudioReadState: "failed",
        pageStates: { ...(base().pageStates || {}), [route]: "guarded" }
      });
      return null;
    }
  }

  async function hydrateContentVariantHistory(briefId, variantId) {
    if (!validContentBriefId(briefId) || !validContentBriefId(variantId)) {
      throw new Error("Mã Content Studio không hợp lệ.");
    }
    const result = await api(`/content-studio/briefs/${encodeURIComponent(String(briefId))}/variants/${encodeURIComponent(String(variantId))}`);
    const data = result.data && typeof result.data === "object" ? result.data : {};
    const variant = data.variant && typeof data.variant === "object" ? data.variant : null;
    if (!variant || String(variant.id || "") !== String(variantId) || String(variant.brief_id || "") !== String(briefId) || !validContentStudioRevision(variant.revision)) {
      throw new Error("History content piece chưa được máy chủ xác nhận.");
    }
    const versions = Array.isArray(data.versions)
      ? data.versions.filter((item) => item && validContentStudioRevision(item.revision)).slice(0, 100)
      : [];
    merge({ contentVariantHistory: { variant_id: String(variantId), revision: Number(variant.revision), versions } });
    return { variant, versions };
  }

  function voiceStudioPolicyIsSafe(policy) {
    return Boolean(
      policy && typeof policy === "object"
      && policy.execution === "authoring_only"
      && policy.provider_called === false
      && policy.audio_created === false
      && policy.raw_audio_stored === false
      && policy.provider_voice_ids_stored === false
      && policy.telegram_file_ids_stored === false
      && policy.tts === "guarded"
      && policy.voice_clone === "guarded"
      && policy.preview === "guarded"
      && policy.output_delivery === "guarded"
    );
  }

  async function hydrateVoiceStudio(filterValue) {
    // This deliberately queries only the Web-owned Voice Studio API. It must
    // never reuse `/voice/profiles`, generic feature readiness, or any Bot
    // bridge route because its records are not a provider voice vault.
    const filter = voiceStudioFilterPayload(filterValue === undefined ? base().voiceStudioFilter : filterValue);
    try {
      const [summaryResult, policyResult, vaultsResult, eventsResult, referencesResult] = await Promise.all([
        api("/voice-studio/summary"),
        api("/voice-studio/policy"),
        api(voiceStudioVaultListPath(filter)),
        api("/voice-studio/events?limit=50"),
        api("/voice-studio/references")
      ]);
      const policy = policyResult.data && typeof policyResult.data === "object" ? policyResult.data : {};
      if (!voiceStudioPolicyIsSafe(policy)) throw new Error("Boundary Voice Studio chưa được máy chủ xác nhận.");
      const vaults = vaultsResult.data && Array.isArray(vaultsResult.data.items)
        ? vaultsResult.data.items.filter((item) => item && validVoiceStudioVaultId(item.id) && validVoiceStudioRevision(item.revision)).slice(0, 100)
        : [];
      const events = eventsResult.data && Array.isArray(eventsResult.data.items)
        ? eventsResult.data.items.filter((item) => item && validVoiceStudioVaultId(item.vault_id) && validVoiceStudioRevision(item.revision)).slice(0, 50)
        : [];
      merge({
        voiceStudioSummary: summaryResult.data && typeof summaryResult.data === "object" ? summaryResult.data : {},
        voiceStudioPolicy: policy,
        voiceVaults: vaults,
        voiceStudioEvents: events,
        voiceStudioReferences: referencesResult.data && typeof referencesResult.data === "object" ? referencesResult.data : {},
        voiceVaultDetail: {},
        voiceCueSheet: {},
        voiceStudioFilter: filter,
        voiceStudioReadState: "ready",
        pageStates: { ...(base().pageStates || {}), "/voice-studio": "ready", "/voice-studio/new": "ready" }
      });
      return { vaults, events };
    } catch (_) {
      // The content here can contain private script/consent references. Clear
      // every projection rather than showing stale account-scoped metadata.
      merge({
        voiceStudioSummary: {}, voiceStudioPolicy: {}, voiceVaults: [], voiceVaultDetail: {}, voiceStudioReferences: {},
        voiceStudioEvents: [], voiceCueSheet: {}, voiceStudioFilter: filter, voiceStudioReadState: "failed",
        pageStates: { ...(base().pageStates || {}), "/voice-studio": "guarded", "/voice-studio/new": "guarded" }
      });
      return { vaults: [], events: [] };
    }
  }

  async function hydrateVoiceVault(vaultId) {
    if (!validVoiceStudioVaultId(vaultId)) throw new Error("Mã Voice Vault không hợp lệ.");
    const route = "/voice-studio/" + encodeURIComponent(String(vaultId));
    try {
      const [detailResult, policyResult, referencesResult] = await Promise.all([
        api("/voice-studio/vaults/" + encodeURIComponent(String(vaultId))),
        api("/voice-studio/policy"),
        api("/voice-studio/references")
      ]);
      const data = detailResult.data && typeof detailResult.data === "object" ? detailResult.data : {};
      const policy = policyResult.data && typeof policyResult.data === "object" ? policyResult.data : {};
      const vault = data.vault && typeof data.vault === "object" ? data.vault : null;
      if (!voiceStudioPolicyIsSafe(policy) || !vault || !validVoiceStudioVaultId(vault.id) || String(vault.id) !== String(vaultId) || !validVoiceStudioRevision(vault.revision)) {
        throw new Error("Voice Vault không còn khả dụng cho Web account hiện tại.");
      }
      const scripts = Array.isArray(data.scripts)
        ? data.scripts.filter((item) => item && validVoiceStudioScriptId(item.id) && String(item.vault_id || "") === String(vaultId) && validVoiceStudioRevision(item.revision)).slice(0, 250)
        : [];
      const versions = Array.isArray(data.versions)
        ? data.versions.filter((item) => item && validVoiceStudioRevision(item.revision)).slice(0, 100)
        : [];
      const events = Array.isArray(data.events)
        ? data.events.filter((item) => item && typeof item === "object" && validVoiceStudioRevision(item.revision)).slice(0, 50)
        : [];
      merge({
        voiceVaultDetail: {
          vault, scripts, versions, events,
          script_count: Number(data.script_count || scripts.length), script_limit: Number(data.script_limit || 250),
          references: data.references && typeof data.references === "object" ? data.references : {}
        },
        voiceStudioPolicy: policy,
        voiceStudioReferences: referencesResult.data && typeof referencesResult.data === "object" ? referencesResult.data : {},
        voiceCueSheet: {},
        voiceStudioReadState: "ready",
        // The detail itself is owner-scoped and safely hydrated, but an active
        // Voice Vault remains editable. Marking the page read-only here would
        // contradict the available CSRF-protected authoring controls.
        pageStates: { ...(base().pageStates || {}), [route]: "ready" }
      });
      return { vault, scripts, versions };
    } catch (_) {
      merge({
        voiceStudioSummary: {}, voiceVaults: [], voiceVaultDetail: {}, voiceStudioReferences: {}, voiceStudioEvents: [],
        voiceStudioPolicy: {}, voiceCueSheet: {}, voiceStudioReadState: "failed",
        pageStates: { ...(base().pageStates || {}), [route]: "guarded" }
      });
      return null;
    }
  }

  async function hydrateVoiceCueSheet(vaultId, scriptId) {
    if (!validVoiceStudioVaultId(vaultId) || !validVoiceStudioScriptId(scriptId)) throw new Error("Mã Voice Vault hoặc script không hợp lệ.");
    const result = await api(`/voice-studio/vaults/${encodeURIComponent(String(vaultId))}/scripts/${encodeURIComponent(String(scriptId))}/cue-sheet`);
    const data = result.data && typeof result.data === "object" ? result.data : {};
    const items = Array.isArray(data.items) ? data.items.filter((item) => item && typeof item === "object").slice(0, 200) : [];
    if (
      String(data.script_id || "") !== String(scriptId)
      || data.execution !== "local_deterministic_writing_aid"
      || data.provider_called !== false
      || data.audio_created !== false
      || !data.metrics || typeof data.metrics !== "object"
    ) {
      throw new Error("Máy chủ chưa trả cue-sheet cục bộ hợp lệ.");
    }
    merge({ voiceCueSheet: { ...data, items, vault_id: String(vaultId), script_id: String(scriptId) } });
    return { ...data, items };
  }

  async function hydrateVideoStudio() {
    // This deliberately requests only the signed Web-owned Video Production
    // Studio API.  It must not reuse the legacy `/video/*` feature state.
    try {
      const [summaryResult, plansResult, eventsResult, referencesResult] = await Promise.all([
        api("/video-studio/summary"),
        api("/video-studio/plans"),
        api("/video-studio/events?limit=50"),
        api("/video-studio/references")
      ]);
      const summary = summaryResult.data && typeof summaryResult.data === "object" ? summaryResult.data : {};
      if (!videoStudioBoundaryIsSafe(summary)) throw new Error("Boundary Video Production Studio chưa được máy chủ xác nhận.");
      const plans = plansResult.data && Array.isArray(plansResult.data.items)
        ? plansResult.data.items.filter((item) => item && validVideoStudioPlanId(item.id) && validVideoStudioRevision(item.revision)).slice(0, 100)
        : [];
      const events = eventsResult.data && Array.isArray(eventsResult.data.items)
        ? eventsResult.data.items.filter((item) => item && validVideoStudioPlanId(item.plan_id) && validVideoStudioRevision(item.revision)).slice(0, 50)
        : [];
      merge({
        videoStudioSummary: summary, videoPlans: plans, videoStudioEvents: events,
        videoStudioReferences: referencesResult.data && typeof referencesResult.data === "object" ? referencesResult.data : {},
        videoPlanDetail: {}, videoPlanEstimate: {}, videoStudioReadState: "ready",
        pageStates: { ...(base().pageStates || {}), "/video-studio": "ready", "/video-studio/new": "ready" }
      });
      return { plans, events };
    } catch (_) {
      merge({
        videoStudioSummary: {}, videoPlans: [], videoPlanDetail: {}, videoPlanEstimate: {}, videoStudioReferences: {}, videoStudioEvents: [],
        videoStudioReadState: "failed", pageStates: { ...(base().pageStates || {}), "/video-studio": "guarded", "/video-studio/new": "guarded" }
      });
      return { plans: [], events: [] };
    }
  }

  async function hydrateVideoPlan(planId) {
    if (!validVideoStudioPlanId(planId)) throw new Error("Mã video plan không hợp lệ.");
    const route = "/video-studio/" + encodeURIComponent(String(planId));
    try {
      const [detailResult, referencesResult] = await Promise.all([
        api("/video-studio/plans/" + encodeURIComponent(String(planId))),
        api("/video-studio/references")
      ]);
      const data = detailResult.data && typeof detailResult.data === "object" ? detailResult.data : {};
      const plan = data.plan && typeof data.plan === "object" ? data.plan : null;
      if (!videoStudioBoundaryIsSafe(data) || !plan || !validVideoStudioPlanId(plan.id) || String(plan.id) !== String(planId) || !validVideoStudioRevision(plan.revision)) {
        throw new Error("Video plan không còn khả dụng cho Web account hiện tại.");
      }
      const archived = String(plan.state || "") === "archived";
      let estimate = {};
      if (!archived) {
        const estimateResult = await api("/video-studio/plans/" + encodeURIComponent(String(planId)) + "/estimate");
        estimate = estimateResult.data && typeof estimateResult.data === "object" ? estimateResult.data : {};
        if (!videoStudioBoundaryIsSafe(estimate)) throw new Error("Máy chủ chưa xác nhận runtime estimate an toàn.");
      }
      const scenes = Array.isArray(data.scenes)
        ? data.scenes.filter((item) => item && validVideoStudioSceneId(item.id) && String(item.plan_id || "") === String(planId) && validVideoStudioRevision(item.revision)).slice(0, 250)
        : [];
      const versions = Array.isArray(data.versions)
        ? data.versions.filter((item) => item && validVideoStudioRevision(item.revision)).slice(0, 100)
        : [];
      const events = Array.isArray(data.events)
        ? data.events.filter((item) => item && typeof item === "object" && validVideoStudioRevision(item.revision)).slice(0, 50)
        : [];
      merge({
        videoPlanDetail: { plan, scenes, versions, events, references: data.references && typeof data.references === "object" ? data.references : {}, estimate },
        videoPlanEstimate: estimate,
        videoStudioReferences: referencesResult.data && typeof referencesResult.data === "object" ? referencesResult.data : {},
        videoStudioReadState: "ready", pageStates: { ...(base().pageStates || {}), [route]: archived ? "archived" : "ready" }
      });
      return { plan, scenes, versions, estimate };
    } catch (_) {
      merge({
        videoStudioSummary: {}, videoPlans: [], videoPlanDetail: {}, videoPlanEstimate: {}, videoStudioReferences: {}, videoStudioEvents: [],
        videoStudioReadState: "failed", pageStates: { ...(base().pageStates || {}), [route]: "guarded" }
      });
      return null;
    }
  }

  async function hydrateImageStudio() {
    // Read only the private Image Studio API.  `/image`, `/image/edit` and
    // `/image/resize` remain separate product surfaces and must never fill
    // artboard state, references or history after this signed read fails.
    try {
      const [summaryResult, artboardsResult, eventsResult, referencesResult, policyResult] = await Promise.all([
        api("/image-studio/summary"),
        api("/image-studio/artboards"),
        api("/image-studio/events?limit=50"),
        api("/image-studio/references"),
        api("/image-studio/policy")
      ]);
      const summary = summaryResult.data && typeof summaryResult.data === "object" ? summaryResult.data : {};
      const references = referencesResult.data && typeof referencesResult.data === "object" ? referencesResult.data : {};
      const policy = policyResult.data && typeof policyResult.data === "object" ? policyResult.data : {};
      if (!imageStudioBoundaryIsSafe(summary) || !imageStudioBoundaryIsSafe(references) || !imageStudioBoundaryIsSafe(policy)) throw new Error("Boundary Image Studio chưa được máy chủ xác nhận.");
      const artboards = artboardsResult.data && Array.isArray(artboardsResult.data.items)
        ? artboardsResult.data.items.filter((item) => item && validImageStudioArtboardId(item.id) && validImageStudioRevision(item.revision)).slice(0, 100)
        : [];
      const events = eventsResult.data && Array.isArray(eventsResult.data.items)
        ? eventsResult.data.items.filter((item) => item && validImageStudioArtboardId(item.artboard_id) && validImageStudioRevision(item.revision)).slice(0, 50)
        : [];
      merge({
        imageStudioSummary: summary, imageArtboards: artboards, imageStudioEvents: events, imageStudioReferences: references, imageStudioPolicy: policy,
        imageArtboardDetail: {}, imageArtboardEstimate: {}, imageStudioReadState: "ready",
        pageStates: { ...(base().pageStates || {}), "/image-studio": "ready", "/image-studio/new": "ready" }
      });
      return { artboards, events };
    } catch (_) {
      merge({
        imageStudioSummary: {}, imageArtboards: [], imageArtboardDetail: {}, imageArtboardEstimate: {}, imageStudioReferences: {}, imageStudioEvents: [], imageStudioPolicy: {},
        imageStudioReadState: "failed", pageStates: { ...(base().pageStates || {}), "/image-studio": "guarded", "/image-studio/new": "guarded" }
      });
      return { artboards: [], events: [] };
    }
  }

  async function hydrateImageArtboard(artboardId) {
    if (!validImageStudioArtboardId(artboardId)) throw new Error("Mã artboard Image Studio không hợp lệ.");
    const route = "/image-studio/" + encodeURIComponent(String(artboardId));
    try {
      const [detailResult, referencesResult, policyResult] = await Promise.all([
        api("/image-studio/artboards/" + encodeURIComponent(String(artboardId))),
        api("/image-studio/references"),
        api("/image-studio/policy")
      ]);
      const data = detailResult.data && typeof detailResult.data === "object" ? detailResult.data : {};
      const references = referencesResult.data && typeof referencesResult.data === "object" ? referencesResult.data : {};
      const policy = policyResult.data && typeof policyResult.data === "object" ? policyResult.data : {};
      const artboard = data.artboard && typeof data.artboard === "object" ? data.artboard : null;
      if (!imageStudioBoundaryIsSafe(data) || !imageStudioBoundaryIsSafe(references) || !imageStudioBoundaryIsSafe(policy) || !artboard || !validImageStudioArtboardId(artboard.id) || String(artboard.id) !== String(artboardId) || !validImageStudioRevision(artboard.revision)) {
        throw new Error("Artboard không còn khả dụng cho Web account hiện tại.");
      }
      const archived = String(artboard.state || "") === "archived";
      let estimate = {};
      if (!archived) {
        const estimateResult = await api("/image-studio/artboards/" + encodeURIComponent(String(artboardId)) + "/estimate");
        estimate = estimateResult.data && typeof estimateResult.data === "object" ? estimateResult.data : {};
        if (!imageStudioBoundaryIsSafe(estimate)) throw new Error("Máy chủ chưa xác nhận review estimate Image Studio an toàn.");
      }
      const directions = Array.isArray(data.directions)
        ? data.directions.filter((item) => item && validImageStudioDirectionId(item.id) && String(item.artboard_id || "") === String(artboardId) && validImageStudioRevision(item.revision)).slice(0, 250)
        : [];
      const versions = Array.isArray(data.versions)
        ? data.versions.filter((item) => item && validImageStudioRevision(item.revision)).slice(0, 100)
        : [];
      const events = Array.isArray(data.events)
        ? data.events.filter((item) => item && typeof item === "object" && validImageStudioRevision(item.revision)).slice(0, 50)
        : [];
      merge({
        imageArtboardDetail: { artboard, directions, versions, events, references: data.references && typeof data.references === "object" ? data.references : {}, estimate },
        imageArtboardEstimate: estimate, imageStudioReferences: references, imageStudioPolicy: policy, imageStudioReadState: "ready",
        pageStates: { ...(base().pageStates || {}), [route]: archived ? "archived" : "ready" }
      });
      return { artboard, directions, versions, estimate };
    } catch (_) {
      merge({
        imageStudioSummary: {}, imageArtboards: [], imageArtboardDetail: {}, imageArtboardEstimate: {}, imageStudioReferences: {}, imageStudioEvents: [], imageStudioPolicy: {},
        imageStudioReadState: "failed", pageStates: { ...(base().pageStates || {}), [route]: "guarded" }
      });
      return null;
    }
  }

  const CHAT_WORKSPACE_LIST_LIMIT = 50;
  // A slow prior filter/page read must never overwrite the most recent
  // signed library view. This is an in-memory ordering guard only; no
  // conversation metadata or query is persisted in the browser.
  let chatWorkspaceHydrationEpoch = 0;
  function chatWorkspaceListOptions(overrides) {
    const saved = base().chatWorkspaceListing && typeof base().chatWorkspaceListing === "object" ? base().chatWorkspaceListing : {};
    const requested = { ...saved, ...(overrides && typeof overrides === "object" ? overrides : {}) };
    const state = CHAT_WORKSPACE_STATES.has(String(requested.state || "")) || String(requested.state || "") === "all"
      ? String(requested.state || "all") : "all";
    const q = String(requested.q || "").replace(/\s+/g, " ").trim();
    const safeQuery = q.length <= 100 && !chatWorkspaceSafetyError(q) ? q : "";
    const savedPagination = saved.pagination && typeof saved.pagination === "object" ? saved.pagination : {};
    const rawOffset = Number(Object.prototype.hasOwnProperty.call(requested, "offset") ? requested.offset : savedPagination.offset);
    const offset = Number.isInteger(rawOffset) && rawOffset > 0 ? rawOffset : 0;
    return { state, q: safeQuery, offset, limit: CHAT_WORKSPACE_LIST_LIMIT };
  }
  function chatWorkspaceThreadsPath(options) {
    const query = [
      "state=" + encodeURIComponent(options.state),
      "limit=" + encodeURIComponent(String(options.limit)),
      "offset=" + encodeURIComponent(String(options.offset))
    ];
    if (options.q) query.push("q=" + encodeURIComponent(options.q));
    return "/chat-workspace/threads?" + query.join("&");
  }
  function chatWorkspacePagination(data, requested) {
    const raw = data && data.pagination && typeof data.pagination === "object" ? data.pagination : {};
    const number = (value, fallback, maximum) => {
      const parsed = Number(value);
      return Number.isInteger(parsed) && parsed >= 0 && parsed <= maximum ? parsed : fallback;
    };
    const total = number(raw.total, 0, 500);
    const limit = number(raw.limit, requested.limit, 100) || requested.limit;
    const offset = number(raw.offset, requested.offset, Math.max(0, total));
    const returned = number(raw.returned, 0, limit);
    const nextOffset = raw.next_offset === null || raw.next_offset === undefined ? null : number(raw.next_offset, -1, Math.max(0, total));
    const previousOffset = raw.previous_offset === null || raw.previous_offset === undefined ? null : number(raw.previous_offset, -1, Math.max(0, total));
    return {
      total, limit, offset, returned,
      has_more: raw.has_more === true && nextOffset !== -1,
      next_offset: nextOffset === -1 ? null : nextOffset,
      previous_offset: previousOffset === -1 ? null : previousOffset
    };
  }

  async function hydrateChatWorkspace(overrides) {
    // Only use the signed, Web-native API. A failed read must never be
    // replaced by a legacy Bot transcript, generic feature bridge or cache.
    const requestEpoch = ++chatWorkspaceHydrationEpoch;
    try {
      const requested = chatWorkspaceListOptions(overrides);
      const results = await Promise.all([
        api("/chat-workspace/summary"),
        api(chatWorkspaceThreadsPath(requested)),
        api("/chat-workspace/events?limit=50"),
        api("/chat-workspace/references"),
        api("/chat-workspace/policy")
      ]);
      const summary = results[0].data && typeof results[0].data === "object" ? results[0].data : {};
      const threadListing = results[1].data && typeof results[1].data === "object" ? results[1].data : {};
      const eventListing = results[2].data && typeof results[2].data === "object" ? results[2].data : {};
      const references = results[3].data && typeof results[3].data === "object" ? results[3].data : {};
      const policy = results[4].data && typeof results[4].data === "object" ? results[4].data : {};
      if (!chatWorkspaceBoundaryIsSafe(summary) || !chatWorkspaceBoundaryIsSafe(threadListing) || !chatWorkspaceBoundaryIsSafe(eventListing) || !chatWorkspaceBoundaryIsSafe(references) || !chatWorkspaceBoundaryIsSafe(policy)) throw new Error("Boundary AI Chat Workspace chưa được máy chủ xác nhận.");
      const threads = Array.isArray(threadListing.items)
        ? threadListing.items.filter((item) => item && validChatWorkspaceId(item.id) && validChatWorkspaceRevision(item.revision) && CHAT_WORKSPACE_MODES.has(String(item.mode || "")) && CHAT_WORKSPACE_STATES.has(String(item.state || ""))).slice(0, CHAT_WORKSPACE_LIST_LIMIT)
        : [];
      const events = Array.isArray(eventListing.items)
        ? eventListing.items.filter((item) => item && validChatWorkspaceId(item.thread_id) && validChatWorkspaceRevision(item.revision)).slice(0, 50)
        : [];
      const serverFilter = threadListing.filter && typeof threadListing.filter === "object" ? threadListing.filter : {};
      const serverQuery = String(serverFilter.q || "").replace(/\s+/g, " ").trim();
      if (serverQuery.length > 100 || chatWorkspaceSafetyError(serverQuery)) throw new Error("Máy chủ trả bộ lọc Chat Workspace không an toàn.");
      const pagination = chatWorkspacePagination(threadListing, requested);
      if (pagination.returned !== threads.length) throw new Error("Máy chủ trả số lượng hội thoại không nhất quán.");
      const listing = {
        state: CHAT_WORKSPACE_STATES.has(String(serverFilter.state || "")) || String(serverFilter.state || "") === "all" ? String(serverFilter.state || "all") : requested.state,
        q: serverQuery,
        pagination
      };
      if (requestEpoch !== chatWorkspaceHydrationEpoch) return { stale: true };
      merge({
        chatWorkspaceSummary: summary, chatThreads: threads, chatWorkspaceEvents: events,
        chatWorkspaceReferences: references, chatWorkspacePolicy: policy, chatWorkspaceListing: listing,
        chatThreadDetail: {}, chatWorkspaceReadState: "ready",
        pageStates: { ...(base().pageStates || {}), "/chat": "ready", "/chat/new": "ready" }
      });
      return { threads, events, listing };
    } catch (_) {
      if (requestEpoch !== chatWorkspaceHydrationEpoch) return { stale: true };
      merge({
        chatWorkspaceSummary: {}, chatThreads: [], chatWorkspaceEvents: [], chatWorkspaceReferences: {}, chatWorkspacePolicy: {}, chatThreadDetail: {},
        chatWorkspaceListing: { state: "all", q: "", pagination: { total: 0, limit: CHAT_WORKSPACE_LIST_LIMIT, offset: 0, returned: 0, has_more: false, next_offset: null, previous_offset: null } },
        chatWorkspaceReadState: "failed", pageStates: { ...(base().pageStates || {}), "/chat": "guarded", "/chat/new": "guarded" }
      });
      return { threads: [], events: [], listing: {} };
    }
  }

  async function hydrateChatThread(threadId) {
    if (!validChatWorkspaceId(threadId)) throw new Error("Mã hội thoại AI Chat Workspace không hợp lệ.");
    const route = "/chat/" + encodeURIComponent(String(threadId));
    try {
      const results = await Promise.all([
        api("/chat-workspace/threads/" + encodeURIComponent(String(threadId))),
        api("/chat-workspace/references"),
        api("/chat-workspace/policy")
      ]);
      const data = results[0].data && typeof results[0].data === "object" ? results[0].data : {};
      const references = results[1].data && typeof results[1].data === "object" ? results[1].data : {};
      const policy = results[2].data && typeof results[2].data === "object" ? results[2].data : {};
      const thread = data.thread && typeof data.thread === "object" ? data.thread : null;
      if (!chatWorkspaceBoundaryIsSafe(data) || !chatWorkspaceBoundaryIsSafe(references) || !chatWorkspaceBoundaryIsSafe(policy) || !thread || !validChatWorkspaceId(thread.id) || String(thread.id) !== String(threadId) || !validChatWorkspaceRevision(thread.revision) || !CHAT_WORKSPACE_MODES.has(String(thread.mode || "")) || !CHAT_WORKSPACE_STATES.has(String(thread.state || ""))) {
        throw new Error("Thread AI Chat Workspace không còn khả dụng cho Web account hiện tại.");
      }
      const contexts = Array.isArray(data.contexts) ? data.contexts.filter((item) => item && validChatWorkspaceId(item.id) && String(item.thread_id || "") === String(threadId) && validChatWorkspaceRevision(item.revision) && CHAT_CONTEXT_KINDS.has(String(item.kind || "")) && ["active", "archived"].includes(String(item.state || ""))).slice(0, 80) : [];
      const turns = Array.isArray(data.turns) ? data.turns.filter((item) => item && validChatWorkspaceId(item.id) && String(item.thread_id || "") === String(threadId) && validChatWorkspaceRevision(item.revision) && CHAT_TURN_KINDS.has(String(item.kind || "")) && ["active", "archived"].includes(String(item.state || ""))).slice(0, 99) : [];
      const versions = Array.isArray(data.versions) ? data.versions.filter((item) => item && validChatWorkspaceRevision(item.revision) && CHAT_WORKSPACE_MODES.has(String(item.mode || "")) && CHAT_WORKSPACE_STATES.has(String(item.state || ""))).slice(0, 100) : [];
      const events = Array.isArray(data.events) ? data.events.filter((item) => item && typeof item === "object" && validChatWorkspaceRevision(item.revision)).slice(0, 50) : [];
      merge({
        chatThreadDetail: { thread, contexts, turns, versions, events, references: data.references && typeof data.references === "object" ? data.references : {} },
        chatWorkspaceReferences: references, chatWorkspacePolicy: policy, chatWorkspaceReadState: "ready",
        pageStates: { ...(base().pageStates || {}), [route]: String(thread.state || "guarded") === "draft" ? "ready" : String(thread.state || "guarded") }
      });
      return { thread, contexts, turns, versions };
    } catch (_) {
      merge({
        chatWorkspaceSummary: {}, chatThreads: [], chatWorkspaceEvents: [], chatWorkspaceReferences: {}, chatWorkspacePolicy: {}, chatThreadDetail: {}, chatWorkspaceListing: { state: "all", q: "", pagination: { total: 0, limit: CHAT_WORKSPACE_LIST_LIMIT, offset: 0, returned: 0, has_more: false, next_offset: null, previous_offset: null } },
        chatWorkspaceReadState: "failed", pageStates: { ...(base().pageStates || {}), [route]: "guarded" }
      });
      return null;
    }
  }

  const ANALYTICS_WORKSPACE_LIST_LIMIT = 50;
  // A stale search/page response must never replace the last signed report
  // library. This ordering guard is memory-only: query values are not stored
  // in the URL, localStorage or any Bot-facing state.
  let analyticsWorkspaceHydrationEpoch = 0;
  function analyticsWorkspaceListOptions(overrides) {
    const saved = base().analyticsWorkspaceListing && typeof base().analyticsWorkspaceListing === "object" ? base().analyticsWorkspaceListing : {};
    const requested = { ...saved, ...(overrides && typeof overrides === "object" ? overrides : {}) };
    const state = ANALYTICS_REPORT_STATES.has(String(requested.state || "")) || String(requested.state || "") === "all" ? String(requested.state || "all") : "all";
    const q = String(requested.q || "").replace(/\s+/g, " ").trim();
    const safeQuery = q.length <= 100 && !analyticsWorkspaceSafetyError(q) && !/^\s*[=+@]/.test(q) ? q : "";
    const savedPagination = saved.pagination && typeof saved.pagination === "object" ? saved.pagination : {};
    const rawOffset = Number(Object.prototype.hasOwnProperty.call(requested, "offset") ? requested.offset : savedPagination.offset);
    const offset = Number.isInteger(rawOffset) && rawOffset > 0 ? rawOffset : 0;
    return { state, q: safeQuery, offset, limit: ANALYTICS_WORKSPACE_LIST_LIMIT };
  }
  function analyticsWorkspaceReportsPath(options) {
    const query = [
      "state=" + encodeURIComponent(options.state),
      "limit=" + encodeURIComponent(String(options.limit)),
      "offset=" + encodeURIComponent(String(options.offset))
    ];
    if (options.q) query.push("q=" + encodeURIComponent(options.q));
    return "/analytics-workspace/reports?" + query.join("&");
  }
  function analyticsWorkspacePagination(data, requested) {
    const raw = data && data.pagination && typeof data.pagination === "object" ? data.pagination : {};
    const number = (value, fallback, maximum) => {
      const parsed = Number(value);
      return Number.isInteger(parsed) && parsed >= 0 && parsed <= maximum ? parsed : fallback;
    };
    const total = number(raw.total, 0, 500);
    const limit = number(raw.limit, requested.limit, 100) || requested.limit;
    const offset = number(raw.offset, requested.offset, Math.max(0, total));
    const returned = number(raw.returned, 0, limit);
    const nextOffset = raw.next_offset === null || raw.next_offset === undefined ? null : number(raw.next_offset, -1, Math.max(0, total));
    const previousOffset = raw.previous_offset === null || raw.previous_offset === undefined ? null : number(raw.previous_offset, -1, Math.max(0, total));
    return { total, limit, offset, returned, has_more: raw.has_more === true && nextOffset !== -1, next_offset: nextOffset === -1 ? null : nextOffset, previous_offset: previousOffset === -1 ? null : previousOffset };
  }
  function analyticsReportListingIsSafe(item) {
    return Boolean(item && validAnalyticsWorkspaceId(item.id) && validAnalyticsRevision(item.revision) && ANALYTICS_REPORT_STATES.has(String(item.state || ""))
      && /^\d{4}-\d{2}-\d{2}$/.test(String(item.period_start || "")) && /^\d{4}-\d{2}-\d{2}$/.test(String(item.period_end || ""))
      && item.data_origin === "user_supplied_only" && item.platform_data_verified === false);
  }
  async function hydrateAnalyticsWorkspace(overrides) {
    // Only the signed Web-native manual analytics API can hydrate this page.
    // A failed request is never substituted with Bot reports, social data or
    // an optimistic browser chart.
    const requestEpoch = ++analyticsWorkspaceHydrationEpoch;
    try {
      const requested = analyticsWorkspaceListOptions(overrides);
      const results = await Promise.all([
        api("/analytics-workspace/summary"),
        api(analyticsWorkspaceReportsPath(requested)),
        api("/analytics-workspace/references"),
        api("/analytics-workspace/policy")
      ]);
      const summary = results[0].data && typeof results[0].data === "object" ? results[0].data : {};
      const listingData = results[1].data && typeof results[1].data === "object" ? results[1].data : {};
      const references = results[2].data && typeof results[2].data === "object" ? results[2].data : {};
      const policy = results[3].data && typeof results[3].data === "object" ? results[3].data : {};
      if (!analyticsWorkspaceBoundaryIsSafe(summary) || !analyticsWorkspaceBoundaryIsSafe(listingData) || !analyticsWorkspaceBoundaryIsSafe(references) || !analyticsWorkspaceBoundaryIsSafe(policy)) throw new Error("Boundary Analytics Workspace chưa được máy chủ xác nhận.");
      const reports = Array.isArray(listingData.items) ? listingData.items.filter(analyticsReportListingIsSafe).slice(0, ANALYTICS_WORKSPACE_LIST_LIMIT) : [];
      const serverFilter = listingData.filter && typeof listingData.filter === "object" ? listingData.filter : {};
      const serverQuery = String(serverFilter.q || "").replace(/\s+/g, " ").trim();
      if (serverQuery.length > 100 || analyticsWorkspaceSafetyError(serverQuery) || /^\s*[=+@]/.test(serverQuery)) throw new Error("Máy chủ trả bộ lọc Analytics Workspace không an toàn.");
      const pagination = analyticsWorkspacePagination(listingData, requested);
      if (pagination.returned !== reports.length) throw new Error("Máy chủ trả số lượng report không nhất quán.");
      const listing = { state: ANALYTICS_REPORT_STATES.has(String(serverFilter.state || "")) || String(serverFilter.state || "") === "all" ? String(serverFilter.state || "all") : requested.state, q: serverQuery, pagination };
      if (requestEpoch !== analyticsWorkspaceHydrationEpoch) return { stale: true };
      merge({
        analyticsWorkspaceSummary: summary, analyticsReports: reports, analyticsWorkspaceReferences: references, analyticsWorkspacePolicy: policy,
        analyticsWorkspaceListing: listing, analyticsReportDetail: {}, analyticsWorkspaceReadState: "ready",
        pageStates: { ...(base().pageStates || {}), "/analytics": "ready", "/analytics/new": "ready" }
      });
      return { reports, listing };
    } catch (_) {
      if (requestEpoch !== analyticsWorkspaceHydrationEpoch) return { stale: true };
      merge({
        analyticsWorkspaceSummary: {}, analyticsReports: [], analyticsReportDetail: {}, analyticsWorkspaceReferences: {}, analyticsWorkspacePolicy: {},
        analyticsWorkspaceListing: { state: "all", q: "", pagination: { total: 0, limit: ANALYTICS_WORKSPACE_LIST_LIMIT, offset: 0, returned: 0, has_more: false, next_offset: null, previous_offset: null } },
        analyticsWorkspaceReadState: "failed", pageStates: { ...(base().pageStates || {}), "/analytics": "guarded", "/analytics/new": "guarded" }
      });
      return { reports: [], listing: {} };
    }
  }
  async function hydrateAnalyticsReport(reportId) {
    if (!validAnalyticsWorkspaceId(reportId)) throw new Error("Mã report Analytics Workspace không hợp lệ.");
    const route = "/analytics/" + encodeURIComponent(String(reportId));
    try {
      const results = await Promise.all([
        api("/analytics-workspace/reports/" + encodeURIComponent(String(reportId))),
        api("/analytics-workspace/references"),
        api("/analytics-workspace/policy")
      ]);
      const data = results[0].data && typeof results[0].data === "object" ? results[0].data : {};
      const references = results[1].data && typeof results[1].data === "object" ? results[1].data : {};
      const policy = results[2].data && typeof results[2].data === "object" ? results[2].data : {};
      const report = data.report && typeof data.report === "object" ? data.report : null;
      if (!analyticsWorkspaceBoundaryIsSafe(data) || !analyticsWorkspaceBoundaryIsSafe(references) || !analyticsWorkspaceBoundaryIsSafe(policy) || !analyticsReportListingIsSafe(report) || String(report.id) !== String(reportId)) throw new Error("Report Analytics Workspace không còn khả dụng cho Web account hiện tại.");
      const metrics = Array.isArray(data.metrics) ? data.metrics.filter((item) => item && validAnalyticsWorkspaceId(item.id) && String(item.report_id || "") === String(reportId) && validAnalyticsRevision(item.revision) && ANALYTICS_METRIC_UNITS.has(String(item.unit || "")) && ANALYTICS_METRIC_DIRECTIONS.has(String(item.direction || "")) && ANALYTICS_METRIC_STATES.has(String(item.state || ""))).slice(0, 120) : [];
      const metricIds = new Set(metrics.map((item) => String(item.id)));
      const snapshots = Array.isArray(data.snapshots) ? data.snapshots.filter((item) => item && validAnalyticsWorkspaceId(item.id) && String(item.report_id || "") === String(reportId) && metricIds.has(String(item.metric_id || "")) && validAnalyticsRevision(item.revision) && ANALYTICS_METRIC_STATES.has(String(item.state || "")) && /^\d{4}-\d{2}-\d{2}$/.test(String(item.observed_on || "")) && item.source_kind === "manual_entry" && item.platform_data_verified === false).slice(0, 12000) : [];
      const findings = Array.isArray(data.findings) ? data.findings.filter((item) => item && validAnalyticsWorkspaceId(item.id) && String(item.report_id || "") === String(reportId) && validAnalyticsRevision(item.revision) && ANALYTICS_FINDING_KINDS.has(String(item.kind || "")) && ANALYTICS_FINDING_STATES.has(String(item.state || "")) && item.ai_recommendation_created === false).slice(0, 320) : [];
      const comparisons = data.comparisons && typeof data.comparisons === "object" ? Object.fromEntries(Object.entries(data.comparisons).filter(([metricId, item]) => metricIds.has(String(metricId)) && item && typeof item === "object")) : {};
      const versions = Array.isArray(data.versions) ? data.versions.filter((item) => item && validAnalyticsRevision(item.revision) && ANALYTICS_REPORT_STATES.has(String(item.state || "")) && item.restore_scope === "metadata_only").slice(0, 100) : [];
      const events = Array.isArray(data.events) ? data.events.filter((item) => item && typeof item === "object" && validAnalyticsRevision(item.revision)).slice(0, 60) : [];
      merge({
        analyticsReportDetail: { report, metrics, snapshots, findings, comparisons, versions, events, references: data.references && typeof data.references === "object" ? data.references : {} },
        analyticsWorkspaceReferences: references, analyticsWorkspacePolicy: policy, analyticsWorkspaceReadState: "ready",
        pageStates: { ...(base().pageStates || {}), [route]: String(report.state || "guarded") === "draft" ? "ready" : String(report.state || "guarded") }
      });
      return { report, metrics, snapshots, findings };
    } catch (_) {
      merge({
        analyticsWorkspaceSummary: {}, analyticsReports: [], analyticsReportDetail: {}, analyticsWorkspaceReferences: {}, analyticsWorkspacePolicy: {},
        analyticsWorkspaceListing: { state: "all", q: "", pagination: { total: 0, limit: ANALYTICS_WORKSPACE_LIST_LIMIT, offset: 0, returned: 0, has_more: false, next_offset: null, previous_offset: null } },
        analyticsWorkspaceReadState: "failed", pageStates: { ...(base().pageStates || {}), [route]: "guarded" }
      });
      return null;
    }
  }

  async function hydrateDocumentWorkspace() {
    // This is intentionally isolated from legacy document operations. A
    // failed private read must never repurpose output/history from /documents.
    try {
      const results = await Promise.all([
        api("/document-workspace/summary"),
        api("/document-workspace/workspaces"),
        api("/document-workspace/events?limit=50"),
        api("/document-workspace/references"),
        api("/document-workspace/policy")
      ]);
      const summary = results[0].data && typeof results[0].data === "object" ? results[0].data : {};
      const references = results[3].data && typeof results[3].data === "object" ? results[3].data : {};
      const policy = results[4].data && typeof results[4].data === "object" ? results[4].data : {};
      if (!documentWorkspaceBoundaryIsSafe(summary) || !documentWorkspaceBoundaryIsSafe(references) || !documentWorkspaceBoundaryIsSafe(policy)) {
        throw new Error("Boundary Document & PDF Workspace chưa được máy chủ xác nhận.");
      }
      const workspaces = results[1].data && Array.isArray(results[1].data.items)
        ? results[1].data.items.filter((item) => item && validDocumentWorkspaceId(item.id) && validDocumentWorkspaceRevision(item.revision)).slice(0, 100) : [];
      const events = results[2].data && Array.isArray(results[2].data.items)
        ? results[2].data.items.filter((item) => item && validDocumentWorkspaceId(item.workspace_id) && validDocumentWorkspaceRevision(item.revision)).slice(0, 50) : [];
      merge({
        documentWorkspaceSummary: summary, documentWorkspaces: workspaces, documentWorkspaceEvents: events,
        documentWorkspaceReferences: references, documentWorkspacePolicy: policy,
        documentWorkspaceDetail: {}, documentWorkspaceEstimate: {}, documentWorkspaceReadState: "ready",
        pageStates: { ...(base().pageStates || {}), "/document-workspace": "ready", "/document-workspace/new": "ready" }
      });
      return { workspaces, events };
    } catch (_) {
      merge({
        documentWorkspaceSummary: {}, documentWorkspaces: [], documentWorkspaceEvents: [],
        documentWorkspaceReferences: {}, documentWorkspacePolicy: {}, documentWorkspaceDetail: {}, documentWorkspaceEstimate: {},
        documentWorkspaceReadState: "failed",
        pageStates: { ...(base().pageStates || {}), "/document-workspace": "guarded", "/document-workspace/new": "guarded" }
      });
      return { workspaces: [], events: [] };
    }
  }

  async function hydrateDocumentWorkspaceDetail(workspaceId) {
    if (!validDocumentWorkspaceId(workspaceId)) throw new Error("Mã Document Workspace không hợp lệ.");
    const route = "/document-workspace/" + encodeURIComponent(String(workspaceId));
    try {
      const results = await Promise.all([
        api("/document-workspace/workspaces/" + encodeURIComponent(String(workspaceId))),
        api("/document-workspace/references"),
        api("/document-workspace/policy")
      ]);
      const data = results[0].data && typeof results[0].data === "object" ? results[0].data : {};
      const references = results[1].data && typeof results[1].data === "object" ? results[1].data : {};
      const policy = results[2].data && typeof results[2].data === "object" ? results[2].data : {};
      const workspace = data.workspace && typeof data.workspace === "object" ? data.workspace : null;
      if (!documentWorkspaceBoundaryIsSafe(data) || !documentWorkspaceBoundaryIsSafe(references) || !documentWorkspaceBoundaryIsSafe(policy) || !workspace || !validDocumentWorkspaceId(workspace.id) || String(workspace.id) !== String(workspaceId) || !validDocumentWorkspaceRevision(workspace.revision)) {
        throw new Error("Document workspace không còn khả dụng cho Web account hiện tại.");
      }
      const writable = String(workspace.state || workspace.lifecycle || "") === "draft";
      let estimate = {};
      if (writable) {
        const estimateResult = await api("/document-workspace/workspaces/" + encodeURIComponent(String(workspaceId)) + "/estimate");
        estimate = estimateResult.data && typeof estimateResult.data === "object" ? estimateResult.data : {};
        if (!documentWorkspaceBoundaryIsSafe(estimate)) throw new Error("Máy chủ chưa xác nhận document plan checklist an toàn.");
      }
      const plans = Array.isArray(data.plans)
        ? data.plans.filter((item) => item && validDocumentPlanId(item.id) && String(item.workspace_id || "") === String(workspaceId) && validDocumentWorkspaceRevision(item.revision)).slice(0, 250) : [];
      const versions = Array.isArray(data.versions)
        ? data.versions.filter((item) => item && validDocumentWorkspaceRevision(item.revision)).slice(0, 100) : [];
      const events = Array.isArray(data.events)
        ? data.events.filter((item) => item && typeof item === "object" && validDocumentWorkspaceRevision(item.revision)).slice(0, 50) : [];
      merge({
        documentWorkspaceDetail: { workspace, plans, versions, events, references: data.references && typeof data.references === "object" ? data.references : {}, estimate },
        documentWorkspaceEstimate: estimate, documentWorkspaceReferences: references, documentWorkspacePolicy: policy,
        documentWorkspaceReadState: "ready",
        pageStates: { ...(base().pageStates || {}), [route]: writable ? "ready" : String(workspace.state || workspace.lifecycle || "guarded") }
      });
      return { workspace, plans, versions, estimate };
    } catch (_) {
      merge({
        documentWorkspaceSummary: {}, documentWorkspaces: [], documentWorkspaceEvents: [],
        documentWorkspaceReferences: {}, documentWorkspacePolicy: {}, documentWorkspaceDetail: {}, documentWorkspaceEstimate: {},
        documentWorkspaceReadState: "failed", pageStates: { ...(base().pageStates || {}), [route]: "guarded" }
      });
      return null;
    }
  }

  async function hydrateSubtitleStudio() {
    // Use only the signed Web-owned Subtitle Studio API.  It must never read
    // broad legacy `/subtitle`, `/translate`, `/dubbing` or `/asr` state.
    try {
      const [summaryResult, projectsResult, eventsResult, referencesResult] = await Promise.all([
        api("/subtitle-studio/summary"),
        api("/subtitle-studio/projects"),
        api("/subtitle-studio/events?limit=50"),
        api("/subtitle-studio/references")
      ]);
      const summary = summaryResult.data && typeof summaryResult.data === "object" ? summaryResult.data : {};
      if (!subtitleStudioBoundaryIsSafe(summary)) throw new Error("Boundary Subtitle Studio chưa được máy chủ xác nhận.");
      const projects = projectsResult.data && Array.isArray(projectsResult.data.items)
        ? projectsResult.data.items.filter((item) => item && validSubtitleStudioProjectId(item.id) && validSubtitleStudioRevision(item.revision)).slice(0, 100)
        : [];
      const events = eventsResult.data && Array.isArray(eventsResult.data.items)
        ? eventsResult.data.items.filter((item) => item && validSubtitleStudioProjectId(item.project_id) && validSubtitleStudioRevision(item.revision)).slice(0, 50)
        : [];
      merge({
        subtitleStudioSummary: summary, subtitleProjects: projects, subtitleStudioEvents: events,
        subtitleStudioReferences: referencesResult.data && typeof referencesResult.data === "object" ? referencesResult.data : {},
        subtitleProjectDetail: {}, subtitleProjectEstimate: {}, subtitleStudioReadState: "ready",
        pageStates: { ...(base().pageStates || {}), "/subtitle-studio": "ready", "/subtitle-studio/new": "ready" }
      });
      return { projects, events };
    } catch (_) {
      merge({
        subtitleStudioSummary: {}, subtitleProjects: [], subtitleProjectDetail: {}, subtitleProjectEstimate: {}, subtitleStudioReferences: {}, subtitleStudioEvents: [],
        subtitleStudioReadState: "failed", pageStates: { ...(base().pageStates || {}), "/subtitle-studio": "guarded", "/subtitle-studio/new": "guarded" }
      });
      return { projects: [], events: [] };
    }
  }

  async function hydrateSubtitleProject(projectId) {
    if (!validSubtitleStudioProjectId(projectId)) throw new Error("Mã transcript project không hợp lệ.");
    const route = "/subtitle-studio/" + encodeURIComponent(String(projectId));
    try {
      const [detailResult, referencesResult] = await Promise.all([
        api("/subtitle-studio/projects/" + encodeURIComponent(String(projectId))),
        api("/subtitle-studio/references")
      ]);
      const data = detailResult.data && typeof detailResult.data === "object" ? detailResult.data : {};
      const project = data.project && typeof data.project === "object" ? data.project : null;
      if (!subtitleStudioBoundaryIsSafe(data) || !project || !validSubtitleStudioProjectId(project.id) || String(project.id) !== String(projectId) || !validSubtitleStudioRevision(project.revision)) {
        throw new Error("Transcript project không còn khả dụng cho Web account hiện tại.");
      }
      const archived = String(project.state || "") === "archived";
      let estimate = {};
      if (!archived) {
        const estimateResult = await api("/subtitle-studio/projects/" + encodeURIComponent(String(projectId)) + "/estimate");
        estimate = estimateResult.data && typeof estimateResult.data === "object" ? estimateResult.data : {};
        if (!subtitleStudioBoundaryIsSafe(estimate)) throw new Error("Máy chủ chưa xác nhận timeline estimate an toàn.");
      }
      const cues = Array.isArray(data.cues)
        ? data.cues.filter((item) => item && validSubtitleStudioCueId(item.id) && String(item.project_id || "") === String(projectId) && validSubtitleStudioRevision(item.revision)).slice(0, 250)
        : [];
      const versions = Array.isArray(data.versions)
        ? data.versions.filter((item) => item && validSubtitleStudioRevision(item.revision)).slice(0, 100)
        : [];
      const events = Array.isArray(data.events)
        ? data.events.filter((item) => item && typeof item === "object" && validSubtitleStudioRevision(item.revision)).slice(0, 50)
        : [];
      merge({
        subtitleProjectDetail: { project, cues, versions, events, references: data.references && typeof data.references === "object" ? data.references : {}, estimate },
        subtitleProjectEstimate: estimate,
        subtitleStudioReferences: referencesResult.data && typeof referencesResult.data === "object" ? referencesResult.data : {},
        subtitleStudioReadState: "ready", pageStates: { ...(base().pageStates || {}), [route]: archived ? "archived" : "ready" }
      });
      return { project, cues, versions, estimate };
    } catch (_) {
      merge({
        subtitleStudioSummary: {}, subtitleProjects: [], subtitleProjectDetail: {}, subtitleProjectEstimate: {}, subtitleStudioReferences: {}, subtitleStudioEvents: [],
        subtitleStudioReadState: "failed", pageStates: { ...(base().pageStates || {}), [route]: "guarded" }
      });
      return null;
    }
  }

  async function hydrateSupportDesk(filterValue) {
    // Support Desk is a signed-account Web projection, deliberately separate
    // from `hydrateCanonicalData` and the legacy `/support/tickets` bridge.
    const filter = supportCaseFilterPayload(filterValue === undefined ? base().supportCaseFilter : filterValue);
    try {
      const [summaryResult, casesResult, eventsResult] = await Promise.all([
        api("/support/summary"),
        api(supportCasesPath(filter, false)),
        api("/support/events?limit=40")
      ]);
      const cases = casesResult.data && Array.isArray(casesResult.data.items)
        ? casesResult.data.items.filter((item) => item && validSupportCaseId(item.id)).slice(0, 100)
        : [];
      const events = eventsResult.data && Array.isArray(eventsResult.data.items)
        ? eventsResult.data.items.filter((item) => item && typeof item === "object").slice(0, 100)
        : [];
      const currentPath = (base().path || window.location.pathname).split("?")[0];
      merge({
        supportSummary: summaryResult.data && typeof summaryResult.data === "object" ? summaryResult.data : {},
        supportCases: cases,
        supportEvents: events,
        supportCaseFilter: filter,
        supportReadState: "ready",
        pageStates: { ...(base().pageStates || {}), [currentPath]: "read_only", "/support": "ready", "/tickets": "read_only" }
      });
      return { cases, events };
    } catch (_) {
      const currentPath = (base().path || window.location.pathname).split("?")[0];
      // Never retain an old account's support content after a failed scoped
      // read.  There is no Bot fallback and no browser-side case cache.
      merge({
        supportSummary: {}, supportCases: [], supportEvents: [], supportCaseDetail: {}, supportCaseFilter: filter, supportReadState: "failed",
        pageStates: { ...(base().pageStates || {}), [currentPath]: "guarded", "/support": "guarded", "/tickets": "guarded" }
      });
      return { cases: [], events: [] };
    }
  }

  async function hydrateSupportCase(caseId) {
    if (!validSupportCaseId(caseId)) throw new Error("Mã yêu cầu Support Desk không hợp lệ.");
    try {
      const result = await api(`/support/cases/${encodeURIComponent(String(caseId))}`);
      const detail = result.data && typeof result.data === "object" ? result.data : {};
      const caseItem = detail.case && typeof detail.case === "object" ? detail.case : null;
      if (!caseItem || !validSupportCaseId(caseItem.id) || String(caseItem.id) !== String(caseId)) throw new Error("Yêu cầu không còn thuộc Web account hiện tại.");
      const messages = Array.isArray(detail.messages) ? detail.messages.filter((item) => item && typeof item === "object").slice(0, 500) : [];
      const events = Array.isArray(detail.events) ? detail.events.filter((item) => item && typeof item === "object").slice(0, 300) : [];
      merge({
        supportCaseDetail: { case: caseItem, messages, events, delivery: String(detail.delivery || "web_view_only") },
        supportReadState: "ready",
        pageStates: { ...(base().pageStates || {}), [`/tickets/${caseId}`]: "read_only" }
      });
      return { case: caseItem, messages, events };
    } catch (_) {
      merge({
        supportCaseDetail: {}, supportReadState: "failed",
        pageStates: { ...(base().pageStates || {}), [`/tickets/${caseId}`]: "guarded" }
      });
      return null;
    }
  }

  async function hydrateSupportAdmin(filterValue) {
    // The endpoints itself verifies role_cache (admin/support_manager/
    // support_operator). The client never decides that a signed account is a
    // support operator; it may only request a server-redacted projection.
    const filter = supportCaseFilterPayload(filterValue === undefined ? base().supportAdminCaseFilter : filterValue);
    try {
      const [summaryResult, casesResult] = await Promise.all([
        api("/support/admin/summary"),
        api(supportCasesPath(filter, true))
      ]);
      const summary = summaryResult.data && typeof summaryResult.data === "object" ? summaryResult.data : {};
      const role = String(summary.operator_role || "").trim();
      if (!["manager", "operator"].includes(role)) throw new Error("Máy chủ chưa cấp role Support Desk cho account này.");
      const cases = casesResult.data && Array.isArray(casesResult.data.items)
        ? casesResult.data.items.filter((item) => item && validSupportCaseId(item.id)).slice(0, 100)
        : [];
      merge({
        supportAdminSummary: summary,
        supportAdminCases: cases,
        supportAdminCaseFilter: filter,
        supportAdminReadState: "ready",
        pageStates: { ...(base().pageStates || {}), "/admin/support": "read_only" }
      });
      return { summary, cases };
    } catch (_) {
      merge({
        supportAdminSummary: {}, supportAdminCases: [], supportAdminCaseDetail: {}, supportAdminCaseFilter: filter, supportAdminReadState: "failed",
        pageStates: { ...(base().pageStates || {}), "/admin/support": "guarded" }
      });
      return null;
    }
  }

  async function hydrateSupportAdminCase(caseId) {
    if (!validSupportCaseId(caseId)) throw new Error("Mã yêu cầu Support Desk không hợp lệ.");
    try {
      // Keep the summary read as a server-side proof of the operator role;
      // client-side role/localStorage can never unlock the case detail.
      const [summaryResult, detailResult] = await Promise.all([
        api("/support/admin/summary"),
        api(`/support/admin/cases/${encodeURIComponent(String(caseId))}`)
      ]);
      const summary = summaryResult.data && typeof summaryResult.data === "object" ? summaryResult.data : {};
      const role = String(summary.operator_role || "").trim();
      const detail = detailResult.data && typeof detailResult.data === "object" ? detailResult.data : {};
      const caseItem = detail.case && typeof detail.case === "object" ? detail.case : null;
      if (!["manager", "operator"].includes(role) || !caseItem || !validSupportCaseId(caseItem.id) || String(caseItem.id) !== String(caseId)) {
        throw new Error("Case không còn khả dụng cho role Support Desk này.");
      }
      const messages = Array.isArray(detail.messages) ? detail.messages.filter((item) => item && typeof item === "object").slice(0, 500) : [];
      const events = Array.isArray(detail.events) ? detail.events.filter((item) => item && typeof item === "object").slice(0, 300) : [];
      merge({
        supportAdminSummary: summary,
        supportAdminCaseDetail: { case: caseItem, messages, events, delivery: String(detail.delivery || "web_view_only") },
        supportAdminReadState: "ready",
        pageStates: { ...(base().pageStates || {}), [`/admin/support/${caseId}`]: "read_only" }
      });
      return { summary, case: caseItem, messages, events };
    } catch (_) {
      merge({
        supportAdminCaseDetail: {}, supportAdminReadState: "failed",
        pageStates: { ...(base().pageStates || {}), [`/admin/support/${caseId}`]: "guarded" }
      });
      return null;
    }
  }

  function imageResizePrivateReadPageState(assetState, operationState) {
    if (base().imageResizeEnabled !== true) return "guarded";
    if (assetState === "ready" && operationState === "ready") return "ready";
    if (assetState === "loading" || operationState === "loading") return "processing";
    return "guarded";
  }

  function imageEnhancePrivateReadPageState(assetState, operationState) {
    if (base().imageEnhanceEnabled !== true) return "guarded";
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
          "/image/resize": imageResizePrivateReadPageState("ready", String(base().imageOperationsReadState || "loading")),
          "/image/edit": imageEnhancePrivateReadPageState("ready", String(base().imageEnhanceOperationsReadState || "loading"))
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
          "/image/resize": imageResizePrivateReadPageState("failed", String(base().imageOperationsReadState || "loading")),
          "/image/edit": imageEnhancePrivateReadPageState("failed", String(base().imageEnhanceOperationsReadState || "loading"))
        }
      });
      return [];
    }
  }

  function documentOperationKindForCurrentRoute() {
    const currentPath = String(base().path || window.location.pathname || "").split("?")[0];
    if (currentPath === "/documents/image-to-pdf") return "image_to_pdf";
    if (currentPath === "/documents/pdf-to-images") return "pdf_to_images";
    if (currentPath === "/documents/pdf-to-word") return "pdf_to_word_text";
    return "";
  }

  async function hydrateDocumentOperations() {
    const kind = documentOperationKindForCurrentRoute();
    try {
      const result = kind === "image_to_pdf"
        ? await api("/document-operations?kind=image_to_pdf&limit=100")
        : kind === "pdf_to_images"
        ? await api("/document-operations?kind=pdf_to_images&limit=100")
        : kind === "pdf_to_word_text"
        ? await api("/document-operations?kind=pdf_to_word_text&limit=100")
        : await api("/document-operations");
      const items = result.data && Array.isArray(result.data.items)
        ? result.data.items
          .filter((item) => item && validDocumentOperationId(item.id) && ["pdf_split", "pdf_merge", "pdf_optimize", "image_to_pdf", "pdf_to_images", "pdf_to_word_text"].includes(String(item.kind || "")))
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
          "/documents/pdf-to-images": base().pdfToImagesEnabled === true ? "ready" : "guarded",
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
          "/documents/pdf-to-images": "guarded",
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

  async function hydrateImageEnhanceOperations() {
    try {
      const result = await api("/image-operations?kind=image_enhance&limit=100");
      const items = result.data && Array.isArray(result.data.items)
        ? result.data.items
          .filter((item) => item && validImageOperationId(item.id) && String(item.kind || "") === "image_enhance")
          .slice(0, 100)
        : [];
      merge({
        imageEnhanceOperations: items,
        imageEnhanceOperationsReadState: "ready",
        pageStates: {
          ...(base().pageStates || {}),
          "/image/edit": imageEnhancePrivateReadPageState(String(base().assetVaultReadState || "loading"), "ready")
        }
      });
      return items;
    } catch (_) {
      // Never substitute stale resize records, Bot assets or browser-created
      // output when the owner-scoped Enhance history cannot be read.
      merge({
        imageEnhanceOperations: [],
        imageEnhanceOperationsReadState: "failed",
        pageStates: {
          ...(base().pageStates || {}),
          "/image/edit": imageEnhancePrivateReadPageState(String(base().assetVaultReadState || "loading"), "failed")
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
    // Native authoring workspaces have no generic feature/bridge projection.
    // Return before any canonical endpoint can overwrite their owner-scoped
    // state, including the similarly-prefixed `/voice-studio` route.
    if (isNativeContentStudioPath(path) || isNativeVoiceStudioPath(path) || isNativeVideoStudioPath(path) || isNativeSubtitleStudioPath(path) || isNativeImageStudioPath(path)) return;
    // Keep the canonical Bot Voice/TTS projection intact, but never let its
    // broad historical `/voice*` matcher absorb the independently owned
    // `/voice-studio` workspace.
    const canonicalBotVoiceRoute = path === "/voice" || path.startsWith("/voice/");
    const canonicalVoicePath = path === "/tts" || path === "/dubbing" || canonicalBotVoiceRoute;
    // Keep the historical Video family exact.  `/video-studio` is not a
    // legacy feature child and must never trigger canonical feature reads.
    const canonicalBotVideoRoute = path === "/video" || path.startsWith("/video/");
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
      } else if (path === "/image/resize" || path === "/image/edit") {
        // Native image operations hydrate separately from Asset Vault. Do not
        // request pricing/readiness from the bridge or overwrite the strict
        // server-side guarded/ready state with a generic image feature badge.
      } else if ((path === "/image" || (path.startsWith("/image/") && path !== "/image/history")) || (canonicalBotVideoRoute && !["/video/progress", "/video/preview", "/video/export"].includes(path))) {
        const [pricing, readiness] = await Promise.all([api("/pricing"), api("/features/status")]);
        merge({
          pricingCatalog: pricing.data || {},
          readiness: readiness.data || {},
          pageStates: featurePageStates(base().catalog || [], readiness.data || {}, base().bridge && base().bridge.featureExecutionFeatures)
        });
      } else if (canonicalVoicePath) {
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

  async function contentStudioMutation({ action, route, scope, path, method, payload, onSuccess }) {
    const submission = acquireSubmission(scope, JSON.stringify(payload));
    if (!submission) {
      toast("Thao tác Content Studio đang chờ máy chủ xác nhận.", "error");
      return null;
    }
    let acknowledged = false;
    setActionBusy(action, route, true);
    try {
      const result = await api(path, {
        method: method || "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, idempotency_key: submission.key })
      });
      acknowledged = true;
      if (typeof onSuccess === "function") await onSuccess(result);
      return result;
    } catch (error) {
      acknowledged = Boolean(error && Number.isInteger(error.status) && error.status > 0);
      throw error;
    } finally {
      releaseSubmission(submission);
      if (acknowledged) discardSubmission(scope, submission);
      setActionBusy(action, route, false);
    }
  }

  async function voiceStudioMutation({ action, route, scope, path, method, payload, onSuccess }) {
    // Use the same write discipline as the other Web-native workspaces:
    // browser-generated idempotency, CSRF in `api`, no retry after an
    // acknowledged response, and no client-side success reconstruction.
    const submission = acquireSubmission(scope, JSON.stringify(payload));
    if (!submission) {
      toast("Thao tác Voice Studio đang chờ máy chủ xác nhận.", "error");
      return null;
    }
    let acknowledged = false;
    setActionBusy(action, route, true);
    try {
      const result = await api(path, {
        method: method || "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, idempotency_key: submission.key })
      });
      acknowledged = true;
      if (typeof onSuccess === "function") await onSuccess(result);
      return result;
    } catch (error) {
      acknowledged = Boolean(error && Number.isInteger(error.status) && error.status > 0);
      throw error;
    } finally {
      releaseSubmission(submission);
      if (acknowledged) discardSubmission(scope, submission);
      setActionBusy(action, route, false);
    }
  }

  async function videoStudioMutation({ action, route, scope, path, method, payload, onSuccess }) {
    // Use the same signed write discipline as each other Web-native
    // workspace: CSRF in `api`, a browser idempotency key, no local success
    // reconstruction and no replay after a response is acknowledged.
    const submission = acquireSubmission(scope, JSON.stringify(payload));
    if (!submission) {
      toast("Thao tác Video Production Studio đang chờ máy chủ xác nhận.", "error");
      return null;
    }
    let acknowledged = false;
    setActionBusy(action, route, true);
    try {
      const result = await api(path, {
        method: method || "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, idempotency_key: submission.key })
      });
      acknowledged = true;
      if (typeof onSuccess === "function") await onSuccess(result);
      return result;
    } catch (error) {
      acknowledged = Boolean(error && Number.isInteger(error.status) && error.status > 0);
      throw error;
    } finally {
      releaseSubmission(submission);
      if (acknowledged) discardSubmission(scope, submission);
      setActionBusy(action, route, false);
    }
  }

  async function documentWorkspaceMutation({ action, route, scope, path, method, payload, onSuccess }) {
    // CSRF is injected by api(), and each write has an account-scoped
    // idempotency key. No client-side response synthesizes a file/result.
    const submission = acquireSubmission(scope, JSON.stringify(payload));
    if (!submission) {
      toast("Thao tác Document & PDF Workspace đang chờ máy chủ xác nhận.", "error");
      return null;
    }
    let acknowledged = false;
    setActionBusy(action, route, true);
    try {
      const result = await api(path, {
        method: method || "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, idempotency_key: submission.key })
      });
      acknowledged = true;
      if (typeof onSuccess === "function") await onSuccess(result);
      return result;
    } catch (error) {
      acknowledged = Boolean(error && Number.isInteger(error.status) && error.status > 0);
      throw error;
    } finally {
      releaseSubmission(submission);
      if (acknowledged) discardSubmission(scope, submission);
      setActionBusy(action, route, false);
    }
  }

  async function chatWorkspaceMutation({ action, route, scope, path, method, payload, onSuccess }) {
    // Each Chat write is CSRF-protected and idempotent. Receipts are redacted,
    // so successful mutations must hydrate from the signed server API instead
    // of patching or retaining private prompt/context text in the browser.
    const submission = acquireSubmission(scope, JSON.stringify(payload));
    if (!submission) {
      toast("Thao tác AI Chat Workspace đang chờ máy chủ xác nhận.", "error");
      return null;
    }
    let acknowledged = false;
    setActionBusy(action, route, true);
    try {
      const result = await api(path, {
        method: method || "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, idempotency_key: submission.key })
      });
      acknowledged = true;
      if (typeof onSuccess === "function") await onSuccess(result);
      return result;
    } catch (error) {
      acknowledged = Boolean(error && Number.isInteger(error.status) && error.status > 0);
      throw error;
    } finally {
      releaseSubmission(submission);
      if (acknowledged) discardSubmission(scope, submission);
      setActionBusy(action, route, false);
    }
  }

  async function analyticsWorkspaceMutation({ action, route, scope, path, method, payload, onSuccess }) {
    // Manual Analytics writes are CSRF-protected and idempotent. Mutation
    // receipts are intentionally privacy-preserving, so callers must reload
    // signed list/detail projections rather than patching report text,
    // snapshot values or human-authored findings in the browser.
    const submission = acquireSubmission(scope, JSON.stringify(payload));
    if (!submission) {
      toast("Thao tác Analytics Workspace đang chờ máy chủ xác nhận.", "error");
      return null;
    }
    let acknowledged = false;
    setActionBusy(action, route, true);
    try {
      const result = await api(path, {
        method: method || "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, idempotency_key: submission.key })
      });
      acknowledged = true;
      if (typeof onSuccess === "function") await onSuccess(result);
      return result;
    } catch (error) {
      acknowledged = Boolean(error && Number.isInteger(error.status) && error.status > 0);
      throw error;
    } finally {
      releaseSubmission(submission);
      if (acknowledged) discardSubmission(scope, submission);
      setActionBusy(action, route, false);
    }
  }
  async function refreshAnalyticsWorkspaceAfterMutation(reportId) {
    // Keep list/detail refresh ordered. The list loader deliberately clears
    // private detail state before its signed request, therefore running both
    // concurrently could let an older list refresh blank a newly loaded
    // report. No mutation receipt is used as browser state.
    await hydrateAnalyticsWorkspace();
    if (validAnalyticsWorkspaceId(reportId)) await hydrateAnalyticsReport(reportId);
  }

  async function imageStudioMutation({ action, route, scope, path, method, payload, onSuccess }) {
    // All Image Studio writes remain server-authenticated and idempotent.
    // The browser never reconstructs an image, preview, job, payment or
    // success from a local form submission; it only accepts a safe receipt.
    const submission = acquireSubmission(scope, JSON.stringify(payload));
    if (!submission) {
      toast("Thao tác Image Creative Studio đang chờ máy chủ xác nhận.", "error");
      return null;
    }
    let acknowledged = false;
    setActionBusy(action, route, true);
    try {
      const result = await api(path, {
        method: method || "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, idempotency_key: submission.key })
      });
      acknowledged = true;
      if (typeof onSuccess === "function") await onSuccess(result);
      return result;
    } catch (error) {
      acknowledged = Boolean(error && Number.isInteger(error.status) && error.status > 0);
      throw error;
    } finally {
      releaseSubmission(submission);
      if (acknowledged) discardSubmission(scope, submission);
      setActionBusy(action, route, false);
    }
  }

  async function subtitleStudioMutation({ action, route, scope, path, method, payload, onSuccess }) {
    // Writes stay within the same CSRF/idempotency discipline as every other
    // native workspace.  The browser never infers a successful ASR/translate/
    // TTS/dub/output operation from a local mutation.
    const submission = acquireSubmission(scope, JSON.stringify(payload));
    if (!submission) {
      toast("Thao tác Subtitle Studio đang chờ máy chủ xác nhận.", "error");
      return null;
    }
    let acknowledged = false;
    setActionBusy(action, route, true);
    try {
      const result = await api(path, {
        method: method || "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, idempotency_key: submission.key })
      });
      acknowledged = true;
      if (typeof onSuccess === "function") await onSuccess(result);
      return result;
    } catch (error) {
      acknowledged = Boolean(error && Number.isInteger(error.status) && error.status > 0);
      throw error;
    } finally {
      releaseSubmission(submission);
      if (acknowledged) discardSubmission(scope, submission);
      setActionBusy(action, route, false);
    }
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
      if (action === "prompt-library-filter" || action === "prompt-library-filter-clear") {
        const filter = action === "prompt-library-filter-clear"
          ? { q: "", category: "", platform: "", product_context: "", tag: "", state: "all" }
          : promptLibraryFilterPayload(fields);
        await hydratePromptLibrary(filter);
        toast(filter.q || filter.category || filter.platform || filter.product_context || filter.tag || filter.state !== "all" ? "Đã áp dụng bộ lọc Prompt Library." : "Đã hiển thị toàn bộ template Web riêng tư.");
        return;
      }
      if (action === "prompt-library-refresh") {
        await hydratePromptLibrary();
        toast("Đã làm mới Prompt Library của Web account hiện tại.");
        return;
      }
      if (action === "prompt-library-export") {
        setActionBusy(action, route, true);
        try {
          const result = await downloadPromptLibraryExport();
          toast(result.message);
        } finally {
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "prompt-template-create") {
        const payload = promptTemplatePayload(fields);
        const scope = "prompt-library:template:create";
        const submission = acquireSubmission(scope, JSON.stringify(payload));
        if (!submission) {
          toast("Template đang được lưu. Vui lòng chờ máy chủ xác nhận.", "error");
          return;
        }
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api("/prompt-library/templates", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, idempotency_key: submission.key })
          });
          acknowledged = true;
          await hydratePromptLibrary();
          toast(result.message || "Đã lưu template vào Prompt Library.");
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
      if (action === "prompt-template-update") {
        const templateId = String(detail.promptTemplateId || "").trim();
        const expectedRevision = validPromptTemplateRevision(detail.promptTemplateRevision);
        if (!validPromptTemplateId(templateId) || !expectedRevision) throw new Error("Mã hoặc revision template Prompt Library không hợp lệ.");
        const payload = { ...promptTemplatePayload(fields), expected_revision: expectedRevision };
        const scope = `prompt-library:template:${templateId}:update`;
        const submission = acquireSubmission(scope, JSON.stringify(payload));
        if (!submission) return;
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api(`/prompt-library/templates/${encodeURIComponent(templateId)}`, {
            method: "PATCH", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, idempotency_key: submission.key })
          });
          acknowledged = true;
          await hydratePromptLibrary();
          await hydratePromptTemplate(templateId);
          toast(result.message || "Đã lưu revision template mới.");
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
      if (["prompt-template-archive", "prompt-template-restore", "prompt-template-purge", "prompt-template-duplicate", "prompt-template-restore-version"].includes(action)) {
        const templateId = String(detail.promptTemplateId || "").trim();
        const expectedRevision = validPromptTemplateRevision(detail.promptTemplateRevision);
        if (!validPromptTemplateId(templateId) || !expectedRevision) throw new Error("Mã hoặc revision template Prompt Library không hợp lệ.");
        const operation = action.replace("prompt-template-", "");
        const version = action === "prompt-template-restore-version" ? validPromptTemplateRevision(detail.promptTemplateVersion) : 0;
        if (action === "prompt-template-restore-version" && !version) throw new Error("Revision cần khôi phục không hợp lệ.");
        const scope = `prompt-library:template:${templateId}:${operation}${version ? `:${version}` : ""}`;
        const submission = acquireSubmission(scope, JSON.stringify({ expected_revision: expectedRevision, version }));
        if (!submission) return;
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          let target = `/prompt-library/templates/${encodeURIComponent(templateId)}/${encodeURIComponent(operation)}`;
          let body = { expected_revision: expectedRevision, idempotency_key: submission.key };
          if (action === "prompt-template-restore-version") {
            target = `/prompt-library/templates/${encodeURIComponent(templateId)}/restore-version`;
            body = { ...body, revision: version };
          }
          if (action === "prompt-template-purge") body = { ...body, confirm: true };
          const result = await api(target, {
            method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
          });
          acknowledged = true;
          await hydratePromptLibrary();
          if (action === "prompt-template-purge") {
            toast(result.message || "Đã xóa vĩnh viễn template đã archive.");
            window.location.assign("/prompt-library");
            return;
          }
          await hydratePromptTemplate(templateId);
          toast(result.message || "Đã cập nhật template Prompt Library.");
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
      if (action === "prompt-template-preview") {
        const templateId = String(detail.promptTemplateId || "").trim();
        const expectedRevision = validPromptTemplateRevision(detail.promptTemplateRevision);
        if (!validPromptTemplateId(templateId) || !expectedRevision) throw new Error("Mã hoặc revision template Prompt Library không hợp lệ.");
        const template = base().promptTemplateDetail && base().promptTemplateDetail.template;
        const variables = template && Array.isArray(template.variables) ? template.variables : [];
        const values = Object.create(null);
        variables.forEach((name) => {
          if (!PROMPT_VARIABLE_NAME_PATTERN.test(String(name || "")) || PROMPT_FORBIDDEN_VARIABLE_NAMES.has(String(name).toLowerCase())) return;
          const value = promptLibraryContent(fields[`variable_${name}`], "Giá trị preview", 0, 600);
          values[name] = value;
        });
        const safetyError = promptLibrarySafetyError(...Object.values(values));
        if (safetyError) throw new Error(safetyError);
        setActionBusy(action, route, true);
        try {
          const result = await api(`/prompt-library/templates/${encodeURIComponent(templateId)}/preview`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ expected_revision: expectedRevision, values })
          });
          const preview = result.data && typeof result.data === "object" ? result.data : {};
          if (preview.execution !== "local_preview_only" || typeof preview.prompt_text !== "string") throw new Error("Máy chủ chưa trả preview Prompt Library cục bộ hợp lệ.");
          merge({ promptTemplatePreview: { ...preview, template_id: templateId } });
          toast(result.message || "Đã tạo preview cục bộ.");
        } finally {
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "prompt-library-import") {
        const payload = promptLibraryImportPayload(fields);
        const scope = "prompt-library:import";
        const submission = acquireSubmission(scope, JSON.stringify(payload));
        if (!submission) {
          toast("JSON template đang được import. Vui lòng chờ máy chủ xác nhận.", "error");
          return;
        }
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api("/prompt-library/import", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, idempotency_key: submission.key })
          });
          acknowledged = true;
          await hydratePromptLibrary();
          toast(result.message || "Đã import template vào Prompt Library.");
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
      if (action === "prompt-template-copy") {
        const templateId = String(detail.promptTemplateId || "").trim();
        const template = base().promptTemplateDetail && base().promptTemplateDetail.template;
        if (!validPromptTemplateId(templateId) || !template || String(template.id || "") !== templateId || String(template.state || "") !== "active" || typeof template.prompt_text !== "string") {
          throw new Error("Nội dung template Prompt Library chưa được nạp an toàn.");
        }
        const text = template.prompt_text;
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
        } else {
          const field = document.createElement("textarea");
          field.value = text;
          field.setAttribute("readonly", "");
          field.style.position = "fixed";
          field.style.opacity = "0";
          document.body.appendChild(field);
          field.select();
          const copied = document.execCommand("copy");
          field.remove();
          if (!copied) throw new Error("Trình duyệt chưa cho phép sao chép prompt.");
        }
        toast("Đã sao chép prompt từ template riêng tư. Chưa có AI execution nào được tạo.");
        return;
      }
      if (action === "media-workspace-filter" || action === "media-workspace-filter-clear") {
        const filter = action === "media-workspace-filter-clear"
          ? { q: "", tag: "", prompt_mode: "", state: "all" }
          : mediaWorkspaceFilterPayload(fields);
        await hydrateMediaWorkspace(filter);
        toast(filter.q || filter.tag || filter.prompt_mode || filter.state !== "all" ? "Đã áp dụng bộ lọc Audio Library." : "Đã hiển thị toàn bộ audio collection riêng tư.");
        return;
      }
      if (action === "media-workspace-refresh") {
        const collectionId = mediaWorkspaceCollectionIdFromPath(route);
        if (collectionId) await hydrateMediaCollection(collectionId);
        else await hydrateMediaWorkspace();
        toast("Đã làm mới Audio Library & Briefing của Web account hiện tại.");
        return;
      }
      if (action === "media-collection-create") {
        const payload = mediaCollectionPayload(fields);
        const scope = "media-workspace:collection:create";
        const submission = acquireSubmission(scope, JSON.stringify(payload));
        if (!submission) {
          toast("Collection đang được lưu. Vui lòng chờ máy chủ xác nhận.", "error");
          return;
        }
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api("/media-workspace/collections", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, idempotency_key: submission.key })
          });
          acknowledged = true;
          const collection = result.data && result.data.collection && typeof result.data.collection === "object" ? result.data.collection : null;
          const collectionId = collection && validMediaCollectionId(collection.id) ? String(collection.id) : "";
          await hydrateMediaWorkspace();
          toast(result.message || "Đã tạo Audio Library collection riêng tư.");
          if (collectionId) {
            window.location.assign(`/media-workspace/${encodeURIComponent(collectionId)}`);
            return;
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
      if (action === "media-collection-update") {
        const collectionId = String(detail.mediaCollectionId || "").trim();
        const expectedRevision = validMediaRevision(detail.mediaCollectionRevision);
        if (!validMediaCollectionId(collectionId) || !expectedRevision) throw new Error("Mã hoặc revision Audio Collection không hợp lệ.");
        const payload = { ...mediaCollectionPayload(fields), expected_revision: expectedRevision };
        const scope = `media-workspace:collection:${collectionId}:update`;
        const submission = acquireSubmission(scope, JSON.stringify(payload));
        if (!submission) return;
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api(`/media-workspace/collections/${encodeURIComponent(collectionId)}`, {
            method: "PATCH", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, idempotency_key: submission.key })
          });
          acknowledged = true;
          await hydrateMediaWorkspace();
          await hydrateMediaCollection(collectionId);
          toast(result.message || "Đã lưu revision Audio Collection mới.");
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
      if (["media-collection-archive", "media-collection-restore", "media-collection-duplicate", "media-collection-restore-version"].includes(action)) {
        const collectionId = String(detail.mediaCollectionId || "").trim();
        const expectedRevision = validMediaRevision(detail.mediaCollectionRevision);
        if (!validMediaCollectionId(collectionId) || !expectedRevision) throw new Error("Mã hoặc revision Audio Collection không hợp lệ.");
        const operation = action.replace("media-collection-", "");
        const sourceRevision = action === "media-collection-restore-version" ? validMediaRevision(detail.mediaCollectionVersion) : 0;
        if (action === "media-collection-restore-version" && !sourceRevision) throw new Error("Revision cần khôi phục không hợp lệ.");
        const scope = `media-workspace:collection:${collectionId}:${operation}${sourceRevision ? `:${sourceRevision}` : ""}`;
        const submission = acquireSubmission(scope, JSON.stringify({ expected_revision: expectedRevision, revision: sourceRevision }));
        if (!submission) return;
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          let target = `/media-workspace/collections/${encodeURIComponent(collectionId)}/${encodeURIComponent(operation)}`;
          let body = { expected_revision: expectedRevision, idempotency_key: submission.key };
          if (action === "media-collection-restore-version") {
            target = `/media-workspace/collections/${encodeURIComponent(collectionId)}/restore-version`;
            body = { ...body, revision: sourceRevision };
          }
          const result = await api(target, {
            method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
          });
          acknowledged = true;
          const created = result.data && result.data.collection && typeof result.data.collection === "object" ? result.data.collection : null;
          const createdId = action === "media-collection-duplicate" && created && validMediaCollectionId(created.id) ? String(created.id) : "";
          await hydrateMediaWorkspace();
          toast(result.message || "Đã cập nhật Audio Collection.");
          if (createdId) {
            window.location.assign(`/media-workspace/${encodeURIComponent(createdId)}`);
            return;
          }
          await hydrateMediaCollection(collectionId);
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
      if (action === "media-collection-compose") {
        const collectionId = String(detail.mediaCollectionId || "").trim();
        const expectedRevision = validMediaRevision(detail.mediaCollectionRevision);
        if (!validMediaCollectionId(collectionId) || !expectedRevision) throw new Error("Mã hoặc revision Audio Collection không hợp lệ.");
        setActionBusy(action, route, true);
        try {
          const result = await api(`/media-workspace/collections/${encodeURIComponent(collectionId)}/compose`, {
            method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ expected_revision: expectedRevision })
          });
          const output = result.data && typeof result.data === "object" ? result.data : {};
          const directions = Array.isArray(output.directions) ? output.directions.filter((item) => item && typeof item.prompt === "string").slice(0, 3) : [];
          if (String(output.collection_id || "") !== collectionId || Number(output.revision || 0) !== expectedRevision || output.execution !== "local_deterministic_draft_only" || output.provider_called !== false || output.charge_started !== false || directions.length !== 3) {
            throw new Error("Máy chủ chưa trả local brief directions Audio Library hợp lệ.");
          }
          merge({ mediaComposer: { ...output, directions, collection_id: collectionId } });
          toast(result.message || "Đã tạo 3 hướng brief cục bộ.");
        } finally {
          setActionBusy(action, route, false);
        }
        return;
      }
      if (["media-item-attach", "media-item-update", "media-item-detach"].includes(action)) {
        const collectionId = String(detail.mediaCollectionId || "").trim();
        const expectedRevision = validMediaRevision(detail.mediaCollectionRevision);
        const itemId = String(detail.mediaItemId || "").trim();
        if (!validMediaCollectionId(collectionId) || !expectedRevision) throw new Error("Mã hoặc revision Audio Collection không hợp lệ.");
        if (action !== "media-item-attach" && !validMediaCollectionId(itemId)) throw new Error("Mã audio reference không hợp lệ.");
        const payload = action === "media-item-detach"
          ? { expected_revision: expectedRevision, confirm: true }
          : { ...mediaItemPayload(fields, action === "media-item-attach"), expected_revision: expectedRevision };
        const operation = action.replace("media-item-", "");
        const scope = `media-workspace:collection:${collectionId}:item:${action === "media-item-attach" ? "attach" : `${itemId}:${operation}`}`;
        const submission = acquireSubmission(scope, JSON.stringify(payload));
        if (!submission) return;
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          let target = `/media-workspace/collections/${encodeURIComponent(collectionId)}/items`;
          let method = "POST";
          if (action === "media-item-update") {
            target = `${target}/${encodeURIComponent(itemId)}`;
            method = "PATCH";
          } else if (action === "media-item-detach") {
            target = `${target}/${encodeURIComponent(itemId)}/detach`;
          }
          const result = await api(target, {
            method, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...payload, idempotency_key: submission.key })
          });
          acknowledged = true;
          await hydrateMediaWorkspace();
          await hydrateMediaCollection(collectionId);
          toast(result.message || "Đã cập nhật audio reference riêng tư.");
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
      if (action === "content-studio-filter" || action === "content-studio-filter-clear") {
        const filter = action === "content-studio-filter-clear"
          ? { q: "", tag: "", content_kind: "", state: "all" }
          : contentStudioFilterPayload(fields);
        await hydrateContentStudio(filter);
        toast(filter.q || filter.tag || filter.content_kind || filter.state !== "all" ? "Đã áp dụng bộ lọc Content Studio." : "Đã hiển thị tất cả content brief riêng tư.");
        return;
      }
      if (action === "content-studio-refresh") {
        const briefId = contentBriefIdFromPath(route);
        if (briefId) await hydrateContentBrief(briefId);
        else await hydrateContentStudio();
        toast("Đã làm mới Creative Content Studio của Web account hiện tại.");
        return;
      }
      if (action === "content-brief-create") {
        const payload = contentBriefPayload(fields);
        const scope = "content-studio:brief:create";
        await contentStudioMutation({
          action, route, scope, path: "/content-studio/briefs", payload,
          onSuccess: async (result) => {
            const receipt = result.data && result.data.brief && typeof result.data.brief === "object" ? result.data.brief : null;
            const briefId = receipt && validContentBriefId(receipt.id) ? String(receipt.id) : "";
            if (!briefId || !validContentStudioRevision(receipt.revision)) throw new Error("Máy chủ chưa trả receipt Content Studio brief hợp lệ.");
            await hydrateContentStudio();
            toast(result.message || "Đã tạo Content Studio brief riêng tư.");
            window.location.assign(`/content-studio/${encodeURIComponent(briefId)}`);
          }
        });
        return;
      }
      if (action === "content-brief-update") {
        const briefId = String(detail.contentBriefId || "").trim();
        const expectedRevision = validContentStudioRevision(detail.contentBriefRevision);
        if (!validContentBriefId(briefId) || !expectedRevision) throw new Error("Mã hoặc revision Content Studio brief không hợp lệ.");
        const payload = { ...contentBriefPayload(fields), expected_revision: expectedRevision };
        await contentStudioMutation({
          action, route, scope: `content-studio:brief:${briefId}:update`, method: "PATCH",
          path: `/content-studio/briefs/${encodeURIComponent(briefId)}`, payload,
          onSuccess: async (result) => {
            await hydrateContentBrief(briefId);
            toast(result.message || "Đã lưu revision Content Studio brief mới.");
          }
        });
        return;
      }
      if (["content-brief-archive", "content-brief-restore", "content-brief-duplicate", "content-brief-restore-version"].includes(action)) {
        const briefId = String(detail.contentBriefId || "").trim();
        const expectedRevision = validContentStudioRevision(detail.contentBriefRevision);
        if (!validContentBriefId(briefId) || !expectedRevision) throw new Error("Mã hoặc revision Content Studio brief không hợp lệ.");
        const operation = action.replace("content-brief-", "");
        const targetRevision = action === "content-brief-restore-version" ? validContentStudioRevision(detail.contentBriefVersion) : 0;
        if (action === "content-brief-restore-version" && !targetRevision) throw new Error("Phiên bản brief cần khôi phục không hợp lệ.");
        const payload = action === "content-brief-restore-version"
          ? { expected_revision: expectedRevision, target_revision: targetRevision }
          : { expected_revision: expectedRevision };
        const path = action === "content-brief-restore-version"
          ? `/content-studio/briefs/${encodeURIComponent(briefId)}/restore-version`
          : `/content-studio/briefs/${encodeURIComponent(briefId)}/${encodeURIComponent(operation)}`;
        const scope = `content-studio:brief:${briefId}:${operation}${targetRevision ? `:${targetRevision}` : ""}`;
        await contentStudioMutation({
          action, route, scope, path, payload,
          onSuccess: async (result) => {
            const receipt = result.data && result.data.brief && typeof result.data.brief === "object" ? result.data.brief : null;
            const createdId = action === "content-brief-duplicate" && receipt && validContentBriefId(receipt.id) ? String(receipt.id) : "";
            if (action === "content-brief-duplicate" && !createdId) throw new Error("Máy chủ chưa trả bản sao Content Studio brief hợp lệ.");
            if (createdId) {
              await hydrateContentStudio();
              toast(result.message || "Đã nhân bản Content Studio brief.");
              window.location.assign(`/content-studio/${encodeURIComponent(createdId)}`);
              return;
            }
            await hydrateContentBrief(briefId);
            toast(result.message || "Đã cập nhật Content Studio brief.");
          }
        });
        return;
      }
      if (action === "content-brief-compose") {
        const briefId = String(detail.contentBriefId || "").trim();
        const expectedRevision = validContentStudioRevision(detail.contentBriefRevision);
        if (!validContentBriefId(briefId) || !expectedRevision) throw new Error("Mã hoặc revision Content Studio brief không hợp lệ.");
        await contentStudioMutation({
          action, route, scope: `content-studio:brief:${briefId}:compose`,
          path: `/content-studio/briefs/${encodeURIComponent(briefId)}/compose`, payload: { expected_revision: expectedRevision },
          onSuccess: async (result) => {
            const output = result.data && typeof result.data === "object" ? result.data : {};
            const ids = Array.isArray(output.variant_ids) ? output.variant_ids.filter(validContentBriefId) : [];
            if (output.execution !== "local_deterministic_draft_only" || output.provider_called !== false || output.charge_started !== false || Number(output.variant_count || 0) !== 3 || ids.length !== 3) {
              throw new Error("Máy chủ chưa trả local deterministic Content Studio draft hợp lệ.");
            }
            await hydrateContentBrief(briefId);
            toast(result.message || "Đã tạo 3 khung nháp cục bộ để bạn biên tập.");
          }
        });
        return;
      }
      if (action === "content-variant-create") {
        const briefId = String(detail.contentBriefId || "").trim();
        const expectedRevision = validContentStudioRevision(detail.contentBriefRevision);
        if (!validContentBriefId(briefId) || !expectedRevision) throw new Error("Mã hoặc revision Content Studio brief không hợp lệ.");
        const payload = { ...contentVariantPayload(fields), expected_revision: expectedRevision };
        await contentStudioMutation({
          action, route, scope: `content-studio:brief:${briefId}:variant:create`,
          path: `/content-studio/briefs/${encodeURIComponent(briefId)}/variants`, payload,
          onSuccess: async (result) => {
            const receipt = result.data && result.data.variant && typeof result.data.variant === "object" ? result.data.variant : null;
            if (!receipt || !validContentBriefId(receipt.id) || String(receipt.brief_id || "") !== briefId || receipt.source_kind !== "manual") {
              throw new Error("Máy chủ chưa trả receipt content piece thủ công hợp lệ.");
            }
            await hydrateContentBrief(briefId);
            toast(result.message || "Đã thêm content piece vào brief.");
          }
        });
        return;
      }
      if (action === "content-variant-update") {
        const briefId = String(detail.contentBriefId || "").trim();
        const variantId = String(detail.contentVariantId || "").trim();
        const expectedRevision = validContentStudioRevision(detail.contentVariantRevision);
        if (!validContentBriefId(briefId) || !validContentBriefId(variantId) || !expectedRevision) throw new Error("Mã hoặc revision content piece không hợp lệ.");
        const payload = { ...contentVariantPayload(fields), expected_revision: expectedRevision };
        await contentStudioMutation({
          action, route, scope: `content-studio:brief:${briefId}:variant:${variantId}:update`, method: "PATCH",
          path: `/content-studio/briefs/${encodeURIComponent(briefId)}/variants/${encodeURIComponent(variantId)}`, payload,
          onSuccess: async (result) => {
            await hydrateContentBrief(briefId);
            toast(result.message || "Đã lưu revision content piece mới.");
          }
        });
        return;
      }
      if (["content-variant-archive", "content-variant-restore", "content-variant-duplicate", "content-variant-restore-version"].includes(action)) {
        const briefId = String(detail.contentBriefId || "").trim();
        const variantId = String(detail.contentVariantId || "").trim();
        const expectedRevision = validContentStudioRevision(detail.contentVariantRevision);
        if (!validContentBriefId(briefId) || !validContentBriefId(variantId) || !expectedRevision) throw new Error("Mã hoặc revision content piece không hợp lệ.");
        const operation = action.replace("content-variant-", "");
        const targetRevision = action === "content-variant-restore-version" ? validContentStudioRevision(detail.contentVariantVersion) : 0;
        if (action === "content-variant-restore-version" && !targetRevision) throw new Error("Phiên bản content piece cần khôi phục không hợp lệ.");
        const payload = action === "content-variant-restore-version"
          ? { expected_revision: expectedRevision, target_revision: targetRevision }
          : { expected_revision: expectedRevision };
        const path = action === "content-variant-restore-version"
          ? `/content-studio/briefs/${encodeURIComponent(briefId)}/variants/${encodeURIComponent(variantId)}/restore-version`
          : `/content-studio/briefs/${encodeURIComponent(briefId)}/variants/${encodeURIComponent(variantId)}/${encodeURIComponent(operation)}`;
        const scope = `content-studio:brief:${briefId}:variant:${variantId}:${operation}${targetRevision ? `:${targetRevision}` : ""}`;
        await contentStudioMutation({
          action, route, scope, path, payload,
          onSuccess: async (result) => {
            const receipt = result.data && result.data.variant && typeof result.data.variant === "object" ? result.data.variant : null;
            if (action === "content-variant-duplicate" && (!receipt || !validContentBriefId(receipt.id) || String(receipt.brief_id || "") !== briefId)) {
              throw new Error("Máy chủ chưa trả bản sao content piece hợp lệ.");
            }
            await hydrateContentBrief(briefId);
            toast(result.message || "Đã cập nhật content piece.");
          }
        });
        return;
      }
      if (action === "content-variant-select") {
        const briefId = String(detail.contentBriefId || "").trim();
        const variantId = String(detail.contentVariantId || "").trim();
        const expectedRevision = validContentStudioRevision(detail.contentBriefRevision);
        if (!validContentBriefId(briefId) || !validContentBriefId(variantId) || !expectedRevision) throw new Error("Mã hoặc revision chọn content piece không hợp lệ.");
        await contentStudioMutation({
          action, route, scope: `content-studio:brief:${briefId}:select:${variantId}`,
          path: `/content-studio/briefs/${encodeURIComponent(briefId)}/select-variant`,
          payload: { expected_revision: expectedRevision, variant_id: variantId },
          onSuccess: async (result) => {
            await hydrateContentBrief(briefId);
            toast(result.message || "Đã chọn content piece cho brief.");
          }
        });
        return;
      }
      if (action === "content-variant-history") {
        const briefId = String(detail.contentBriefId || "").trim();
        const variantId = String(detail.contentVariantId || "").trim();
        if (!validContentBriefId(briefId) || !validContentBriefId(variantId)) throw new Error("Mã content piece không hợp lệ.");
        setActionBusy(action, route, true);
        try {
          await hydrateContentVariantHistory(briefId, variantId);
          toast("Đã tải lịch sử content piece riêng tư.");
        } finally {
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "video-studio-refresh") {
        const planId = videoPlanIdFromPath(route);
        if (planId) await hydrateVideoPlan(planId);
        else await hydrateVideoStudio();
        toast("Đã làm mới Video Production Studio của Web account hiện tại.");
        return;
      }
      if (action === "video-plan-create") {
        const payload = videoPlanPayload(fields);
        await videoStudioMutation({
          action, route, scope: "video-studio:plan:create", path: "/video-studio/plans", payload,
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.plan && typeof data.plan === "object" ? data.plan : null;
            const planId = receipt && validVideoStudioPlanId(receipt.id) ? String(receipt.id) : "";
            if (!videoStudioBoundaryIsSafe(data) || !planId || !validVideoStudioRevision(receipt.revision)) {
              throw new Error("Máy chủ chưa trả receipt video plan Web-native hợp lệ.");
            }
            await hydrateVideoStudio();
            toast(result.message || "Đã tạo video plan riêng tư.");
            window.location.assign(`/video-studio/${encodeURIComponent(planId)}`);
          }
        });
        return;
      }
      if (action === "video-plan-update") {
        const planId = String(detail.videoPlanId || "").trim();
        const expectedRevision = validVideoStudioRevision(detail.videoPlanRevision);
        if (!validVideoStudioPlanId(planId) || !expectedRevision) throw new Error("Mã hoặc revision video plan không hợp lệ.");
        const payload = { ...videoPlanPayload(fields), expected_revision: expectedRevision };
        await videoStudioMutation({
          action, route, scope: `video-studio:plan:${planId}:update`, method: "PATCH",
          path: `/video-studio/plans/${encodeURIComponent(planId)}`, payload,
          onSuccess: async (result) => {
            if (!videoStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận revision video plan an toàn.");
            await hydrateVideoStudio();
            await hydrateVideoPlan(planId);
            toast(result.message || "Đã lưu revision video plan mới.");
          }
        });
        return;
      }
      if (action === "video-plan-state") {
        const planId = String(detail.videoPlanId || "").trim();
        const expectedRevision = validVideoStudioRevision(detail.videoPlanRevision);
        const state = String(detail.videoPlanState || "").trim().toLowerCase();
        if (!validVideoStudioPlanId(planId) || !expectedRevision || !VIDEO_STUDIO_PLAN_STATES.has(state)) throw new Error("Trạng thái hoặc revision video plan không hợp lệ.");
        const current = base().videoPlanDetail && base().videoPlanDetail.plan;
        const currentState = current && String(current.id || "") === planId ? String(current.state || "") : "";
        if (currentState === "archived" && state !== "draft") throw new Error("Plan đã archive chỉ có thể được khôi phục về Draft.");
        if (currentState === "approved" && !["draft", "archived"].includes(state)) throw new Error("Plan self-review xong cần về Draft trước khi thay đổi review.");
        await videoStudioMutation({
          action, route, scope: `video-studio:plan:${planId}:state:${state}`,
          path: `/video-studio/plans/${encodeURIComponent(planId)}/lifecycle`, payload: { state, expected_revision: expectedRevision },
          onSuccess: async (result) => {
            const receipt = result.data && result.data.plan && typeof result.data.plan === "object" ? result.data.plan : null;
            if (!videoStudioBoundaryIsSafe(result.data) || !receipt || !validVideoStudioRevision(receipt.revision)) throw new Error("Máy chủ chưa xác nhận trạng thái plan an toàn.");
            await hydrateVideoStudio();
            await hydrateVideoPlan(planId);
            toast(result.message || "Đã cập nhật trạng thái self-review.");
          }
        });
        return;
      }
      if (action === "video-plan-restore-version") {
        const planId = String(detail.videoPlanId || "").trim();
        const expectedRevision = validVideoStudioRevision(detail.videoPlanRevision);
        const targetRevision = validVideoStudioRevision(detail.videoPlanVersion);
        if (!validVideoStudioPlanId(planId) || !expectedRevision || !targetRevision) throw new Error("Version hoặc revision video plan không hợp lệ.");
        await videoStudioMutation({
          action, route, scope: `video-studio:plan:${planId}:restore-version:${targetRevision}`,
          path: `/video-studio/plans/${encodeURIComponent(planId)}/restore-version`, payload: { expected_revision: expectedRevision, target_revision: targetRevision },
          onSuccess: async (result) => {
            if (!videoStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận version video plan an toàn.");
            await hydrateVideoStudio();
            await hydrateVideoPlan(planId);
            toast(result.message || "Đã khôi phục version video plan thành revision mới.");
          }
        });
        return;
      }
      if (action === "video-scene-create") {
        const planId = String(detail.videoPlanId || "").trim();
        const expectedRevision = validVideoStudioRevision(detail.videoPlanRevision);
        if (!validVideoStudioPlanId(planId) || !expectedRevision) throw new Error("Mã hoặc revision video plan không hợp lệ.");
        const payload = { ...videoScenePayload(fields), expected_revision: expectedRevision };
        await videoStudioMutation({
          action, route, scope: `video-studio:plan:${planId}:scene:create`,
          path: `/video-studio/plans/${encodeURIComponent(planId)}/scenes`, payload,
          onSuccess: async (result) => {
            const receipt = result.data && result.data.scene && typeof result.data.scene === "object" ? result.data.scene : null;
            if (!videoStudioBoundaryIsSafe(result.data) || !receipt || !validVideoStudioSceneId(receipt.id) || String(receipt.plan_id || "") !== planId) {
              throw new Error("Máy chủ chưa trả receipt scene hợp lệ.");
            }
            await hydrateVideoStudio();
            await hydrateVideoPlan(planId);
            toast(result.message || "Đã thêm scene riêng tư vào video plan.");
          }
        });
        return;
      }
      if (action === "video-scene-update") {
        const planId = String(detail.videoPlanId || "").trim();
        const sceneId = String(detail.videoSceneId || "").trim();
        const expectedRevision = validVideoStudioRevision(detail.videoSceneRevision);
        if (!validVideoStudioPlanId(planId) || !validVideoStudioSceneId(sceneId) || !expectedRevision) throw new Error("Mã hoặc revision scene không hợp lệ.");
        const payload = { ...videoScenePayload(fields), expected_revision: expectedRevision };
        await videoStudioMutation({
          action, route, scope: `video-studio:plan:${planId}:scene:${sceneId}:update`, method: "PATCH",
          path: `/video-studio/plans/${encodeURIComponent(planId)}/scenes/${encodeURIComponent(sceneId)}`, payload,
          onSuccess: async (result) => {
            if (!videoStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận revision scene an toàn.");
            await hydrateVideoPlan(planId);
            toast(result.message || "Đã lưu revision scene mới.");
          }
        });
        return;
      }
      if (action === "video-scene-archive" || action === "video-scene-restore") {
        const planId = String(detail.videoPlanId || "").trim();
        const sceneId = String(detail.videoSceneId || "").trim();
        const expectedRevision = validVideoStudioRevision(detail.videoSceneRevision);
        if (!validVideoStudioPlanId(planId) || !validVideoStudioSceneId(sceneId) || !expectedRevision) throw new Error("Mã hoặc revision scene không hợp lệ.");
        const operation = action.replace("video-scene-", "");
        await videoStudioMutation({
          action, route, scope: `video-studio:plan:${planId}:scene:${sceneId}:${operation}`,
          path: `/video-studio/plans/${encodeURIComponent(planId)}/scenes/${encodeURIComponent(sceneId)}/${encodeURIComponent(operation)}`,
          payload: { expected_revision: expectedRevision },
          onSuccess: async (result) => {
            if (!videoStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận trạng thái scene an toàn.");
            await hydrateVideoStudio();
            await hydrateVideoPlan(planId);
            toast(result.message || "Đã cập nhật scene.");
          }
        });
        return;
      }
      if (action === "video-scene-restore-version") {
        const planId = String(detail.videoPlanId || "").trim();
        const sceneId = String(detail.videoSceneId || "").trim();
        const expectedRevision = validVideoStudioRevision(detail.videoSceneRevision);
        const targetRevision = validVideoStudioRevision(detail.videoSceneVersion);
        if (!validVideoStudioPlanId(planId) || !validVideoStudioSceneId(sceneId) || !expectedRevision || !targetRevision) throw new Error("Version hoặc revision scene không hợp lệ.");
        await videoStudioMutation({
          action, route, scope: `video-studio:plan:${planId}:scene:${sceneId}:restore-version:${targetRevision}`,
          path: `/video-studio/plans/${encodeURIComponent(planId)}/scenes/${encodeURIComponent(sceneId)}/restore-version`,
          payload: { expected_revision: expectedRevision, target_revision: targetRevision },
          onSuccess: async (result) => {
            if (!videoStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận version scene an toàn.");
            await hydrateVideoPlan(planId);
            toast(result.message || "Đã khôi phục version scene thành revision mới.");
          }
        });
        return;
      }
      if (action === "video-scene-reorder") {
        const planId = String(detail.videoPlanId || "").trim();
        const expectedRevision = validVideoStudioRevision(detail.videoPlanRevision);
        const sceneId = String(detail.videoSceneId || "").trim();
        const direction = String(detail.videoSceneDirection || "").trim().toLowerCase();
        if (!validVideoStudioPlanId(planId) || !expectedRevision || !validVideoStudioSceneId(sceneId) || !["up", "down"].includes(direction)) throw new Error("Yêu cầu sắp xếp scene không hợp lệ.");
        const planDetail = base().videoPlanDetail && typeof base().videoPlanDetail === "object" ? base().videoPlanDetail : {};
        const activeScenes = Array.isArray(planDetail.scenes)
          ? planDetail.scenes.filter((item) => item && String(item.plan_id || "") === planId && String(item.state || "active") === "active" && validVideoStudioSceneId(item.id))
          : [];
        const index = activeScenes.findIndex((item) => String(item.id) === sceneId);
        const target = direction === "up" ? index - 1 : index + 1;
        if (index < 0 || target < 0 || target >= activeScenes.length) throw new Error("Không thể đổi thứ tự scene ở vị trí này.");
        const sceneIds = activeScenes.map((item) => String(item.id));
        [sceneIds[index], sceneIds[target]] = [sceneIds[target], sceneIds[index]];
        await videoStudioMutation({
          action, route, scope: `video-studio:plan:${planId}:scenes:reorder`,
          path: `/video-studio/plans/${encodeURIComponent(planId)}/scenes/reorder`, payload: { expected_revision: expectedRevision, scene_ids: sceneIds },
          onSuccess: async (result) => {
            if (!videoStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận thứ tự scene an toàn.");
            await hydrateVideoPlan(planId);
            toast(result.message || "Đã cập nhật thứ tự scene.");
          }
        });
        return;
      }
      if (action === "chat-workspace-refresh") {
        const threadId = chatThreadIdFromPath(route);
        if (threadId) await hydrateChatThread(threadId);
        else await hydrateChatWorkspace();
        toast("Đã làm mới AI Chat Workspace của Web account hiện tại.");
        return;
      }
      if (action === "chat-workspace-filter") {
        const state = String(fields.state || "all").trim().toLowerCase();
        const q = String(fields.q || "").replace(/\s+/g, " ").trim();
        if (!(state === "all" || CHAT_WORKSPACE_STATES.has(state))) throw new Error("Bộ lọc trạng thái hội thoại không hợp lệ.");
        if (q.length > 100 || chatWorkspaceSafetyError(q)) throw new Error("Từ khoá tìm kiếm hội thoại không hợp lệ.");
        const result = await hydrateChatWorkspace({ state, q, offset: 0 });
        if (!result || result.stale) return;
        const total = result && result.listing && result.listing.pagination ? Number(result.listing.pagination.total || 0) : 0;
        toast(total ? `Đã áp dụng bộ lọc: ${total} hội thoại phù hợp.` : "Không có hội thoại phù hợp với bộ lọc.");
        return;
      }
      if (action === "chat-workspace-page") {
        const offset = Number(fields.__chatWorkspaceOffset);
        if (!Number.isInteger(offset) || offset < 0 || offset > 500) throw new Error("Trang hội thoại không hợp lệ.");
        await hydrateChatWorkspace({ offset });
        return;
      }
      if (action === "chat-thread-create") {
        const payload = chatThreadPayload(fields);
        await chatWorkspaceMutation({
          action, route, scope: "chat-workspace:thread:create", path: "/chat-workspace/threads", payload,
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.thread && typeof data.thread === "object" ? data.thread : null;
            const threadId = receipt && validChatWorkspaceId(receipt.id) ? String(receipt.id) : "";
            if (!chatWorkspaceBoundaryIsSafe(data) || !threadId || !validChatWorkspaceRevision(receipt.revision)) throw new Error("Máy chủ chưa trả receipt thread AI Chat Workspace hợp lệ.");
            await hydrateChatWorkspace();
            toast(result.message || "Đã tạo thread Web-native. AI chưa được gọi.");
            window.location.assign(`/chat/${encodeURIComponent(threadId)}`);
          }
        });
        return;
      }
      if (action === "chat-thread-update") {
        const threadId = String(fields.__chatThreadId || chatThreadIdFromPath(route)).trim();
        const expectedRevision = validChatWorkspaceRevision(fields.__chatThreadRevision);
        if (!validChatWorkspaceId(threadId) || !expectedRevision) throw new Error("Mã hoặc revision thread không hợp lệ.");
        const payload = { ...chatThreadPayload(fields), expected_revision: expectedRevision };
        await chatWorkspaceMutation({
          action, route, scope: `chat-workspace:thread:${threadId}:update`, method: "PATCH",
          path: `/chat-workspace/threads/${encodeURIComponent(threadId)}`, payload,
          onSuccess: async (result) => {
            if (!chatWorkspaceBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận revision thread an toàn.");
            await hydrateChatWorkspace();
            await hydrateChatThread(threadId);
            toast(result.message || "Đã lưu revision thread mới.");
          }
        });
        return;
      }
      if (action === "chat-thread-lifecycle") {
        const threadId = String(fields.__chatThreadId || chatThreadIdFromPath(route)).trim();
        const expectedRevision = validChatWorkspaceRevision(fields.__chatThreadRevision);
        const state = String(fields.__chatThreadState || "").trim().toLowerCase();
        if (!validChatWorkspaceId(threadId) || !expectedRevision || !CHAT_WORKSPACE_STATES.has(state)) throw new Error("Trạng thái hoặc revision thread không hợp lệ.");
        await chatWorkspaceMutation({
          action, route, scope: `chat-workspace:thread:${threadId}:lifecycle:${state}`,
          path: `/chat-workspace/threads/${encodeURIComponent(threadId)}/lifecycle`, payload: { state, expected_revision: expectedRevision },
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.thread && typeof data.thread === "object" ? data.thread : null;
            if (!chatWorkspaceBoundaryIsSafe(data) || !receipt || !validChatWorkspaceRevision(receipt.revision)) throw new Error("Máy chủ chưa xác nhận lifecycle thread an toàn.");
            await hydrateChatWorkspace();
            await hydrateChatThread(threadId);
            toast(result.message || "Đã cập nhật lifecycle thread.");
          }
        });
        return;
      }
      if (action === "chat-thread-restore-version") {
        const threadId = String(fields.__chatThreadId || chatThreadIdFromPath(route)).trim();
        const expectedRevision = validChatWorkspaceRevision(fields.__chatThreadRevision);
        const targetRevision = validChatWorkspaceRevision(fields.__chatThreadVersion);
        if (!validChatWorkspaceId(threadId) || !expectedRevision || !targetRevision) throw new Error("Version hoặc revision thread không hợp lệ.");
        await chatWorkspaceMutation({
          action, route, scope: `chat-workspace:thread:${threadId}:restore:${targetRevision}`,
          path: `/chat-workspace/threads/${encodeURIComponent(threadId)}/restore-version`, payload: { expected_revision: expectedRevision, target_revision: targetRevision },
          onSuccess: async (result) => {
            if (!chatWorkspaceBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận version thread an toàn.");
            await hydrateChatWorkspace();
            await hydrateChatThread(threadId);
            toast(result.message || "Đã khôi phục version thread thành revision mới.");
          }
        });
        return;
      }
      if (action === "chat-context-create") {
        const threadId = String(fields.__chatThreadId || chatThreadIdFromPath(route)).trim();
        const expectedRevision = validChatWorkspaceRevision(fields.__chatThreadRevision);
        if (!validChatWorkspaceId(threadId) || !expectedRevision) throw new Error("Mã hoặc revision thread không hợp lệ.");
        const payload = { ...chatContextPayload(fields), expected_revision: expectedRevision };
        await chatWorkspaceMutation({
          action, route, scope: `chat-workspace:thread:${threadId}:context:create`,
          path: `/chat-workspace/threads/${encodeURIComponent(threadId)}/contexts`, payload,
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.context && typeof data.context === "object" ? data.context : null;
            if (!chatWorkspaceBoundaryIsSafe(data) || !receipt || !validChatWorkspaceId(receipt.id) || String(receipt.thread_id || "") !== threadId || !validChatWorkspaceRevision(receipt.revision)) throw new Error("Máy chủ chưa trả receipt context hợp lệ.");
            await hydrateChatWorkspace();
            await hydrateChatThread(threadId);
            toast(result.message || "Đã thêm context card riêng tư.");
          }
        });
        return;
      }
      if (action === "chat-context-update") {
        const threadId = String(fields.__chatThreadId || chatThreadIdFromPath(route)).trim();
        const contextId = String(fields.__chatContextId || "").trim();
        const expectedRevision = validChatWorkspaceRevision(fields.__chatThreadRevision);
        if (!validChatWorkspaceId(threadId) || !validChatWorkspaceId(contextId) || !expectedRevision) throw new Error("Mã hoặc revision context không hợp lệ.");
        const payload = { ...chatContextPayload(fields), expected_revision: expectedRevision };
        await chatWorkspaceMutation({
          action, route, scope: `chat-workspace:thread:${threadId}:context:${contextId}:update`, method: "PATCH",
          path: `/chat-workspace/threads/${encodeURIComponent(threadId)}/contexts/${encodeURIComponent(contextId)}`, payload,
          onSuccess: async (result) => {
            if (!chatWorkspaceBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận revision context an toàn.");
            await hydrateChatWorkspace();
            await hydrateChatThread(threadId);
            toast(result.message || "Đã lưu revision context mới.");
          }
        });
        return;
      }
      if (action === "chat-context-state") {
        const threadId = String(fields.__chatThreadId || chatThreadIdFromPath(route)).trim();
        const contextId = String(fields.__chatContextId || "").trim();
        const expectedRevision = validChatWorkspaceRevision(fields.__chatThreadRevision);
        const state = String(fields.__chatContextState || "").trim().toLowerCase();
        if (!validChatWorkspaceId(threadId) || !validChatWorkspaceId(contextId) || !expectedRevision || !["active", "archived"].includes(state)) throw new Error("Trạng thái hoặc revision context không hợp lệ.");
        await chatWorkspaceMutation({
          action, route, scope: `chat-workspace:thread:${threadId}:context:${contextId}:${state}`,
          path: `/chat-workspace/threads/${encodeURIComponent(threadId)}/contexts/${encodeURIComponent(contextId)}/state`, payload: { state, expected_revision: expectedRevision },
          onSuccess: async (result) => {
            if (!chatWorkspaceBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận trạng thái context an toàn.");
            await hydrateChatWorkspace();
            await hydrateChatThread(threadId);
            toast(result.message || "Đã cập nhật context card.");
          }
        });
        return;
      }
      if (action === "chat-turn-create") {
        const threadId = String(fields.__chatThreadId || chatThreadIdFromPath(route)).trim();
        const expectedRevision = validChatWorkspaceRevision(fields.__chatThreadRevision);
        if (!validChatWorkspaceId(threadId) || !expectedRevision) throw new Error("Mã hoặc revision thread không hợp lệ.");
        const payload = { ...chatTurnPayload(fields), expected_revision: expectedRevision };
        await chatWorkspaceMutation({
          action, route, scope: `chat-workspace:thread:${threadId}:turn:create`,
          path: `/chat-workspace/threads/${encodeURIComponent(threadId)}/turns`, payload,
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.turn && typeof data.turn === "object" ? data.turn : null;
            if (!chatWorkspaceBoundaryIsSafe(data) || !receipt || !validChatWorkspaceId(receipt.id) || String(receipt.thread_id || "") !== threadId || !validChatWorkspaceRevision(receipt.revision)) throw new Error("Máy chủ chưa trả receipt lượt ghi chú hợp lệ.");
            await hydrateChatWorkspace();
            await hydrateChatThread(threadId);
            toast(result.message || "Đã thêm lượt ghi chú do bạn soạn.");
          }
        });
        return;
      }
      if (action === "chat-turn-state") {
        const threadId = String(fields.__chatThreadId || chatThreadIdFromPath(route)).trim();
        const turnId = String(fields.__chatTurnId || "").trim();
        const expectedRevision = validChatWorkspaceRevision(fields.__chatThreadRevision);
        const state = String(fields.__chatTurnState || "").trim().toLowerCase();
        if (!validChatWorkspaceId(threadId) || !validChatWorkspaceId(turnId) || !expectedRevision || !["active", "archived"].includes(state)) throw new Error("Trạng thái hoặc revision lượt ghi chú không hợp lệ.");
        await chatWorkspaceMutation({
          action, route, scope: `chat-workspace:thread:${threadId}:turn:${turnId}:${state}`,
          path: `/chat-workspace/threads/${encodeURIComponent(threadId)}/turns/${encodeURIComponent(turnId)}/state`, payload: { state, expected_revision: expectedRevision },
          onSuccess: async (result) => {
            if (!chatWorkspaceBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận trạng thái lượt ghi chú an toàn.");
            await hydrateChatWorkspace();
            await hydrateChatThread(threadId);
            toast(result.message || "Đã cập nhật lượt ghi chú.");
          }
        });
        return;
      }
      if (action === "analytics-workspace-refresh") {
        const reportId = analyticsReportIdFromPath(route);
        if (reportId) await hydrateAnalyticsReport(reportId);
        else await hydrateAnalyticsWorkspace();
        toast("Đã làm mới Analytics Workspace của Web account hiện tại.");
        return;
      }
      if (action === "analytics-workspace-filter") {
        const state = String(fields.state || "all").trim().toLowerCase();
        const q = String(fields.q || "").replace(/\s+/g, " ").trim();
        if (!(state === "all" || ANALYTICS_REPORT_STATES.has(state))) throw new Error("Bộ lọc trạng thái report không hợp lệ.");
        if (q.length > 100 || analyticsWorkspaceSafetyError(q) || /^\s*[=+@]/.test(q)) throw new Error("Từ khoá tìm kiếm report không hợp lệ.");
        const result = await hydrateAnalyticsWorkspace({ state, q, offset: 0 });
        if (!result || result.stale) return;
        const total = result.listing && result.listing.pagination ? Number(result.listing.pagination.total || 0) : 0;
        toast(total ? `Đã áp dụng bộ lọc: ${total} report phù hợp.` : "Không có report phù hợp với bộ lọc.");
        return;
      }
      if (action === "analytics-workspace-page") {
        const offset = Number(fields.__analyticsWorkspaceOffset);
        if (!Number.isInteger(offset) || offset < 0 || offset > 500) throw new Error("Trang report không hợp lệ.");
        await hydrateAnalyticsWorkspace({ offset });
        return;
      }
      if (action === "analytics-report-create") {
        const payload = analyticsReportPayload(fields);
        await analyticsWorkspaceMutation({
          action, route, scope: "analytics-workspace:report:create", path: "/analytics-workspace/reports", payload,
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.report && typeof data.report === "object" ? data.report : null;
            const reportId = receipt && validAnalyticsWorkspaceId(receipt.id) ? String(receipt.id) : "";
            if (!analyticsWorkspaceBoundaryIsSafe(data) || !reportId || !validAnalyticsRevision(receipt.revision)) throw new Error("Máy chủ chưa trả receipt report Analytics Workspace hợp lệ.");
            await hydrateAnalyticsWorkspace();
            toast(result.message || "Đã tạo report thủ công riêng tư.");
            window.location.assign(`/analytics/${encodeURIComponent(reportId)}`);
          }
        });
        return;
      }
      if (action === "analytics-report-update") {
        const reportId = String(fields.__analyticsReportId || analyticsReportIdFromPath(route)).trim();
        const expectedRevision = validAnalyticsRevision(fields.__analyticsReportRevision);
        if (!validAnalyticsWorkspaceId(reportId) || !expectedRevision) throw new Error("Mã hoặc revision report không hợp lệ.");
        const payload = { ...analyticsReportPayload(fields), expected_revision: expectedRevision };
        await analyticsWorkspaceMutation({
          action, route, scope: `analytics-workspace:report:${reportId}:update`, method: "PATCH", path: `/analytics-workspace/reports/${encodeURIComponent(reportId)}`, payload,
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.report && typeof data.report === "object" ? data.report : null;
            if (!analyticsWorkspaceBoundaryIsSafe(data) || !receipt || !validAnalyticsWorkspaceId(receipt.id) || String(receipt.id) !== reportId || !validAnalyticsRevision(receipt.revision)) throw new Error("Máy chủ chưa xác nhận revision report an toàn.");
            await refreshAnalyticsWorkspaceAfterMutation(reportId);
            toast(result.message || "Đã lưu revision report mới.");
          }
        });
        return;
      }
      if (action === "analytics-report-lifecycle") {
        const reportId = String(fields.__analyticsReportId || analyticsReportIdFromPath(route)).trim();
        const expectedRevision = validAnalyticsRevision(fields.__analyticsReportRevision);
        const state = String(fields.__analyticsReportState || "").trim().toLowerCase();
        if (!validAnalyticsWorkspaceId(reportId) || !expectedRevision || !ANALYTICS_REPORT_STATES.has(state)) throw new Error("Trạng thái hoặc revision report không hợp lệ.");
        await analyticsWorkspaceMutation({
          action, route, scope: `analytics-workspace:report:${reportId}:lifecycle:${state}`, path: `/analytics-workspace/reports/${encodeURIComponent(reportId)}/lifecycle`, payload: { state, expected_revision: expectedRevision },
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.report && typeof data.report === "object" ? data.report : null;
            if (!analyticsWorkspaceBoundaryIsSafe(data) || !receipt || !validAnalyticsWorkspaceId(receipt.id) || String(receipt.id) !== reportId || !validAnalyticsRevision(receipt.revision)) throw new Error("Máy chủ chưa xác nhận lifecycle report an toàn.");
            await refreshAnalyticsWorkspaceAfterMutation(reportId);
            toast(result.message || "Đã cập nhật trạng thái report.");
          }
        });
        return;
      }
      if (action === "analytics-report-restore-version") {
        const reportId = String(fields.__analyticsReportId || analyticsReportIdFromPath(route)).trim();
        const expectedRevision = validAnalyticsRevision(fields.__analyticsReportRevision);
        const targetRevision = validAnalyticsRevision(fields.__analyticsReportVersion);
        if (!validAnalyticsWorkspaceId(reportId) || !expectedRevision || !targetRevision) throw new Error("Version hoặc revision report không hợp lệ.");
        await analyticsWorkspaceMutation({
          action, route, scope: `analytics-workspace:report:${reportId}:restore:${targetRevision}`, path: `/analytics-workspace/reports/${encodeURIComponent(reportId)}/restore-version`, payload: { expected_revision: expectedRevision, target_revision: targetRevision },
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.report && typeof data.report === "object" ? data.report : null;
            if (!analyticsWorkspaceBoundaryIsSafe(data) || !receipt || !validAnalyticsWorkspaceId(receipt.id) || String(receipt.id) !== reportId || !validAnalyticsRevision(receipt.revision)) throw new Error("Máy chủ chưa xác nhận version report an toàn.");
            await refreshAnalyticsWorkspaceAfterMutation(reportId);
            toast(result.message || "Đã khôi phục metadata report thành revision mới.");
          }
        });
        return;
      }
      if (action === "analytics-metric-create") {
        const reportId = String(fields.__analyticsReportId || analyticsReportIdFromPath(route)).trim();
        const expectedReportRevision = validAnalyticsRevision(fields.__analyticsReportRevision);
        if (!validAnalyticsWorkspaceId(reportId) || !expectedReportRevision) throw new Error("Mã hoặc revision report không hợp lệ.");
        const payload = { ...analyticsMetricPayload(fields), expected_report_revision: expectedReportRevision };
        await analyticsWorkspaceMutation({
          action, route, scope: `analytics-workspace:report:${reportId}:metric:create`, path: `/analytics-workspace/reports/${encodeURIComponent(reportId)}/metrics`, payload,
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.metric && typeof data.metric === "object" ? data.metric : null;
            if (!analyticsWorkspaceBoundaryIsSafe(data) || !receipt || !validAnalyticsWorkspaceId(receipt.id) || String(receipt.report_id || "") !== reportId || !validAnalyticsRevision(receipt.revision)) throw new Error("Máy chủ chưa trả receipt metric hợp lệ.");
            await refreshAnalyticsWorkspaceAfterMutation(reportId);
            toast(result.message || "Đã thêm metric tự định nghĩa.");
          }
        });
        return;
      }
      if (action === "analytics-metric-update") {
        const reportId = String(fields.__analyticsReportId || analyticsReportIdFromPath(route)).trim();
        const metricId = String(fields.__analyticsMetricId || "").trim();
        const expectedReportRevision = validAnalyticsRevision(fields.__analyticsReportRevision);
        const expectedRevision = validAnalyticsRevision(fields.__analyticsMetricRevision);
        if (!validAnalyticsWorkspaceId(reportId) || !validAnalyticsWorkspaceId(metricId) || !expectedReportRevision || !expectedRevision) throw new Error("Mã hoặc revision metric không hợp lệ.");
        const payload = { ...analyticsMetricPayload(fields), expected_report_revision: expectedReportRevision, expected_revision: expectedRevision };
        await analyticsWorkspaceMutation({
          action, route, scope: `analytics-workspace:report:${reportId}:metric:${metricId}:update`, method: "PATCH", path: `/analytics-workspace/reports/${encodeURIComponent(reportId)}/metrics/${encodeURIComponent(metricId)}`, payload,
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.metric && typeof data.metric === "object" ? data.metric : null;
            if (!analyticsWorkspaceBoundaryIsSafe(data) || !receipt || !validAnalyticsWorkspaceId(receipt.id) || String(receipt.id) !== metricId || !validAnalyticsRevision(receipt.revision)) throw new Error("Máy chủ chưa xác nhận revision metric an toàn.");
            await refreshAnalyticsWorkspaceAfterMutation(reportId);
            toast(result.message || "Đã lưu revision metric mới.");
          }
        });
        return;
      }
      if (action === "analytics-metric-state") {
        const reportId = String(fields.__analyticsReportId || analyticsReportIdFromPath(route)).trim();
        const metricId = String(fields.__analyticsMetricId || "").trim();
        const expectedReportRevision = validAnalyticsRevision(fields.__analyticsReportRevision);
        const expectedRevision = validAnalyticsRevision(fields.__analyticsMetricRevision);
        const state = String(fields.__analyticsMetricState || "").trim().toLowerCase();
        if (!validAnalyticsWorkspaceId(reportId) || !validAnalyticsWorkspaceId(metricId) || !expectedReportRevision || !expectedRevision || !ANALYTICS_METRIC_STATES.has(state)) throw new Error("Trạng thái hoặc revision metric không hợp lệ.");
        await analyticsWorkspaceMutation({
          action, route, scope: `analytics-workspace:report:${reportId}:metric:${metricId}:state:${state}`, path: `/analytics-workspace/reports/${encodeURIComponent(reportId)}/metrics/${encodeURIComponent(metricId)}/state`, payload: { state, expected_report_revision: expectedReportRevision, expected_revision: expectedRevision },
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.metric && typeof data.metric === "object" ? data.metric : null;
            if (!analyticsWorkspaceBoundaryIsSafe(data) || !receipt || !validAnalyticsWorkspaceId(receipt.id) || String(receipt.id) !== metricId || !validAnalyticsRevision(receipt.revision)) throw new Error("Máy chủ chưa xác nhận trạng thái metric an toàn.");
            await refreshAnalyticsWorkspaceAfterMutation(reportId);
            toast(result.message || "Đã cập nhật metric.");
          }
        });
        return;
      }
      if (action === "analytics-snapshot-create") {
        const reportId = String(fields.__analyticsReportId || analyticsReportIdFromPath(route)).trim();
        const metricId = String(fields.__analyticsMetricId || "").trim();
        const expectedReportRevision = validAnalyticsRevision(fields.__analyticsReportRevision);
        if (!validAnalyticsWorkspaceId(reportId) || !validAnalyticsWorkspaceId(metricId) || !expectedReportRevision) throw new Error("Mã hoặc revision report/metric không hợp lệ.");
        const payload = { ...analyticsSnapshotPayload(fields), expected_report_revision: expectedReportRevision };
        await analyticsWorkspaceMutation({
          action, route, scope: `analytics-workspace:report:${reportId}:metric:${metricId}:snapshot:create`, path: `/analytics-workspace/reports/${encodeURIComponent(reportId)}/metrics/${encodeURIComponent(metricId)}/snapshots`, payload,
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.snapshot && typeof data.snapshot === "object" ? data.snapshot : null;
            if (!analyticsWorkspaceBoundaryIsSafe(data) || !receipt || !validAnalyticsWorkspaceId(receipt.id) || String(receipt.report_id || "") !== reportId || String(receipt.metric_id || "") !== metricId || !validAnalyticsRevision(receipt.revision)) throw new Error("Máy chủ chưa trả receipt snapshot hợp lệ.");
            await refreshAnalyticsWorkspaceAfterMutation(reportId);
            toast(result.message || "Đã lưu snapshot tự nhập.");
          }
        });
        return;
      }
      if (action === "analytics-snapshot-update") {
        const reportId = String(fields.__analyticsReportId || analyticsReportIdFromPath(route)).trim();
        const metricId = String(fields.__analyticsMetricId || "").trim();
        const snapshotId = String(fields.__analyticsSnapshotId || "").trim();
        const expectedReportRevision = validAnalyticsRevision(fields.__analyticsReportRevision);
        const expectedRevision = validAnalyticsRevision(fields.__analyticsSnapshotRevision);
        if (!validAnalyticsWorkspaceId(reportId) || !validAnalyticsWorkspaceId(metricId) || !validAnalyticsWorkspaceId(snapshotId) || !expectedReportRevision || !expectedRevision) throw new Error("Mã hoặc revision snapshot không hợp lệ.");
        const payload = { ...analyticsSnapshotPayload(fields), expected_report_revision: expectedReportRevision, expected_revision: expectedRevision };
        await analyticsWorkspaceMutation({
          action, route, scope: `analytics-workspace:report:${reportId}:metric:${metricId}:snapshot:${snapshotId}:update`, method: "PATCH", path: `/analytics-workspace/reports/${encodeURIComponent(reportId)}/metrics/${encodeURIComponent(metricId)}/snapshots/${encodeURIComponent(snapshotId)}`, payload,
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.snapshot && typeof data.snapshot === "object" ? data.snapshot : null;
            if (!analyticsWorkspaceBoundaryIsSafe(data) || !receipt || !validAnalyticsWorkspaceId(receipt.id) || String(receipt.id) !== snapshotId || !validAnalyticsRevision(receipt.revision)) throw new Error("Máy chủ chưa xác nhận revision snapshot an toàn.");
            await refreshAnalyticsWorkspaceAfterMutation(reportId);
            toast(result.message || "Đã lưu revision snapshot mới.");
          }
        });
        return;
      }
      if (action === "analytics-snapshot-state") {
        const reportId = String(fields.__analyticsReportId || analyticsReportIdFromPath(route)).trim();
        const metricId = String(fields.__analyticsMetricId || "").trim();
        const snapshotId = String(fields.__analyticsSnapshotId || "").trim();
        const expectedReportRevision = validAnalyticsRevision(fields.__analyticsReportRevision);
        const expectedRevision = validAnalyticsRevision(fields.__analyticsSnapshotRevision);
        const state = String(fields.__analyticsSnapshotState || "").trim().toLowerCase();
        if (!validAnalyticsWorkspaceId(reportId) || !validAnalyticsWorkspaceId(metricId) || !validAnalyticsWorkspaceId(snapshotId) || !expectedReportRevision || !expectedRevision || !ANALYTICS_METRIC_STATES.has(state)) throw new Error("Trạng thái hoặc revision snapshot không hợp lệ.");
        await analyticsWorkspaceMutation({
          action, route, scope: `analytics-workspace:report:${reportId}:metric:${metricId}:snapshot:${snapshotId}:state:${state}`, path: `/analytics-workspace/reports/${encodeURIComponent(reportId)}/metrics/${encodeURIComponent(metricId)}/snapshots/${encodeURIComponent(snapshotId)}/state`, payload: { state, expected_report_revision: expectedReportRevision, expected_revision: expectedRevision },
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.snapshot && typeof data.snapshot === "object" ? data.snapshot : null;
            if (!analyticsWorkspaceBoundaryIsSafe(data) || !receipt || !validAnalyticsWorkspaceId(receipt.id) || String(receipt.id) !== snapshotId || !validAnalyticsRevision(receipt.revision)) throw new Error("Máy chủ chưa xác nhận trạng thái snapshot an toàn.");
            await refreshAnalyticsWorkspaceAfterMutation(reportId);
            toast(result.message || "Đã cập nhật snapshot.");
          }
        });
        return;
      }
      if (action === "analytics-finding-create") {
        const reportId = String(fields.__analyticsReportId || analyticsReportIdFromPath(route)).trim();
        const expectedReportRevision = validAnalyticsRevision(fields.__analyticsReportRevision);
        if (!validAnalyticsWorkspaceId(reportId) || !expectedReportRevision) throw new Error("Mã hoặc revision report không hợp lệ.");
        const payload = { ...analyticsFindingPayload(fields), expected_report_revision: expectedReportRevision };
        await analyticsWorkspaceMutation({
          action, route, scope: `analytics-workspace:report:${reportId}:finding:create`, path: `/analytics-workspace/reports/${encodeURIComponent(reportId)}/findings`, payload,
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.finding && typeof data.finding === "object" ? data.finding : null;
            if (!analyticsWorkspaceBoundaryIsSafe(data) || !receipt || !validAnalyticsWorkspaceId(receipt.id) || String(receipt.report_id || "") !== reportId || !validAnalyticsRevision(receipt.revision)) throw new Error("Máy chủ chưa trả receipt ghi chú hợp lệ.");
            await refreshAnalyticsWorkspaceAfterMutation(reportId);
            toast(result.message || "Đã lưu ghi chú do người viết.");
          }
        });
        return;
      }
      if (action === "analytics-finding-update") {
        const reportId = String(fields.__analyticsReportId || analyticsReportIdFromPath(route)).trim();
        const findingId = String(fields.__analyticsFindingId || "").trim();
        const expectedReportRevision = validAnalyticsRevision(fields.__analyticsReportRevision);
        const expectedRevision = validAnalyticsRevision(fields.__analyticsFindingRevision);
        if (!validAnalyticsWorkspaceId(reportId) || !validAnalyticsWorkspaceId(findingId) || !expectedReportRevision || !expectedRevision) throw new Error("Mã hoặc revision ghi chú không hợp lệ.");
        const payload = { ...analyticsFindingPayload(fields), expected_report_revision: expectedReportRevision, expected_revision: expectedRevision };
        await analyticsWorkspaceMutation({
          action, route, scope: `analytics-workspace:report:${reportId}:finding:${findingId}:update`, method: "PATCH", path: `/analytics-workspace/reports/${encodeURIComponent(reportId)}/findings/${encodeURIComponent(findingId)}`, payload,
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.finding && typeof data.finding === "object" ? data.finding : null;
            if (!analyticsWorkspaceBoundaryIsSafe(data) || !receipt || !validAnalyticsWorkspaceId(receipt.id) || String(receipt.id) !== findingId || !validAnalyticsRevision(receipt.revision)) throw new Error("Máy chủ chưa xác nhận revision ghi chú an toàn.");
            await refreshAnalyticsWorkspaceAfterMutation(reportId);
            toast(result.message || "Đã lưu revision ghi chú mới.");
          }
        });
        return;
      }
      if (action === "analytics-finding-state") {
        const reportId = String(fields.__analyticsReportId || analyticsReportIdFromPath(route)).trim();
        const findingId = String(fields.__analyticsFindingId || "").trim();
        const expectedReportRevision = validAnalyticsRevision(fields.__analyticsReportRevision);
        const expectedRevision = validAnalyticsRevision(fields.__analyticsFindingRevision);
        const state = String(fields.__analyticsFindingState || "").trim().toLowerCase();
        if (!validAnalyticsWorkspaceId(reportId) || !validAnalyticsWorkspaceId(findingId) || !expectedReportRevision || !expectedRevision || !ANALYTICS_FINDING_STATES.has(state)) throw new Error("Trạng thái hoặc revision ghi chú không hợp lệ.");
        await analyticsWorkspaceMutation({
          action, route, scope: `analytics-workspace:report:${reportId}:finding:${findingId}:state:${state}`, path: `/analytics-workspace/reports/${encodeURIComponent(reportId)}/findings/${encodeURIComponent(findingId)}/state`, payload: { state, expected_report_revision: expectedReportRevision, expected_revision: expectedRevision },
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.finding && typeof data.finding === "object" ? data.finding : null;
            if (!analyticsWorkspaceBoundaryIsSafe(data) || !receipt || !validAnalyticsWorkspaceId(receipt.id) || String(receipt.id) !== findingId || !validAnalyticsRevision(receipt.revision)) throw new Error("Máy chủ chưa xác nhận trạng thái ghi chú an toàn.");
            await refreshAnalyticsWorkspaceAfterMutation(reportId);
            toast(result.message || "Đã cập nhật ghi chú.");
          }
        });
        return;
      }
      if (action === "document-workspace-refresh") {
        const workspaceId = documentWorkspaceIdFromPath(route);
        if (workspaceId) await hydrateDocumentWorkspaceDetail(workspaceId);
        else await hydrateDocumentWorkspace();
        toast("Đã làm mới Document & PDF Workspace của Web account hiện tại.");
        return;
      }
      if (action === "document-workspace-create") {
        const payload = documentWorkspacePayload(fields);
        await documentWorkspaceMutation({
          action, route, scope: "document-workspace:create", path: "/document-workspace/workspaces", payload,
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.workspace && typeof data.workspace === "object" ? data.workspace : null;
            const workspaceId = receipt && validDocumentWorkspaceId(receipt.id) ? String(receipt.id) : "";
            if (!documentWorkspaceBoundaryIsSafe(data) || !workspaceId || !validDocumentWorkspaceRevision(receipt.revision)) {
              throw new Error("Máy chủ chưa trả receipt document brief Web-native hợp lệ.");
            }
            await hydrateDocumentWorkspace();
            toast(result.message || "Đã tạo document brief riêng tư.");
            window.location.assign(`/document-workspace/${encodeURIComponent(workspaceId)}`);
          }
        });
        return;
      }
      if (action === "document-workspace-update") {
        const workspaceId = String(fields.__documentWorkspaceId || documentWorkspaceIdFromPath(route)).trim();
        const expectedRevision = validDocumentWorkspaceRevision(fields.__documentWorkspaceRevision);
        if (!validDocumentWorkspaceId(workspaceId) || !expectedRevision) throw new Error("Mã hoặc revision document brief không hợp lệ.");
        const payload = { ...documentWorkspacePayload(fields), expected_revision: expectedRevision };
        await documentWorkspaceMutation({
          action, route, scope: `document-workspace:${workspaceId}:update`, method: "PATCH",
          path: `/document-workspace/workspaces/${encodeURIComponent(workspaceId)}`, payload,
          onSuccess: async (result) => {
            if (!documentWorkspaceBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận revision document brief an toàn.");
            await hydrateDocumentWorkspace();
            await hydrateDocumentWorkspaceDetail(workspaceId);
            toast(result.message || "Đã lưu revision document brief mới.");
          }
        });
        return;
      }
      if (action === "document-workspace-state") {
        const workspaceId = String(fields.__documentWorkspaceId || documentWorkspaceIdFromPath(route)).trim();
        const expectedRevision = validDocumentWorkspaceRevision(fields.__documentWorkspaceRevision);
        const state = String(fields.__documentWorkspaceState || "").trim().toLowerCase();
        if (!validDocumentWorkspaceId(workspaceId) || !expectedRevision || !DOCUMENT_WORKSPACE_STATES.has(state)) throw new Error("Trạng thái hoặc revision document brief không hợp lệ.");
        const current = base().documentWorkspaceDetail && base().documentWorkspaceDetail.workspace;
        const currentState = current && String(current.id || "") === workspaceId ? String(current.state || current.lifecycle || "") : "";
        if (currentState === "archived" && state !== "draft") throw new Error("Document brief đã archive chỉ có thể được khôi phục về Draft.");
        if (currentState === "approved" && !["draft", "archived"].includes(state)) throw new Error("Document brief đã approved cần về Draft trước khi thay đổi review.");
        await documentWorkspaceMutation({
          action, route, scope: `document-workspace:${workspaceId}:state:${state}`,
          path: `/document-workspace/workspaces/${encodeURIComponent(workspaceId)}/lifecycle`, payload: { state, expected_revision: expectedRevision },
          onSuccess: async (result) => {
            const receipt = result.data && result.data.workspace && typeof result.data.workspace === "object" ? result.data.workspace : null;
            if (!documentWorkspaceBoundaryIsSafe(result.data) || !receipt || !validDocumentWorkspaceRevision(receipt.revision)) throw new Error("Máy chủ chưa xác nhận trạng thái document brief an toàn.");
            await hydrateDocumentWorkspace();
            await hydrateDocumentWorkspaceDetail(workspaceId);
            toast(result.message || "Đã cập nhật trạng thái self-review.");
          }
        });
        return;
      }
      if (action === "document-workspace-restore-version") {
        const workspaceId = String(fields.__documentWorkspaceId || documentWorkspaceIdFromPath(route)).trim();
        const expectedRevision = validDocumentWorkspaceRevision(fields.__documentWorkspaceRevision);
        const targetRevision = validDocumentWorkspaceRevision(fields.__documentWorkspaceVersion);
        if (!validDocumentWorkspaceId(workspaceId) || !expectedRevision || !targetRevision) throw new Error("Version hoặc revision document brief không hợp lệ.");
        await documentWorkspaceMutation({
          action, route, scope: `document-workspace:${workspaceId}:restore-version:${targetRevision}`,
          path: `/document-workspace/workspaces/${encodeURIComponent(workspaceId)}/restore-version`, payload: { expected_revision: expectedRevision, target_revision: targetRevision },
          onSuccess: async (result) => {
            if (!documentWorkspaceBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận version document brief an toàn.");
            await hydrateDocumentWorkspace();
            await hydrateDocumentWorkspaceDetail(workspaceId);
            toast(result.message || "Đã khôi phục version brief thành revision mới.");
          }
        });
        return;
      }
      if (action === "document-plan-create") {
        const workspaceId = String(fields.__documentWorkspaceId || documentWorkspaceIdFromPath(route)).trim();
        const expectedRevision = validDocumentWorkspaceRevision(fields.__documentWorkspaceRevision);
        if (!validDocumentWorkspaceId(workspaceId) || !expectedRevision) throw new Error("Mã hoặc revision document brief không hợp lệ.");
        const payload = { ...documentPlanPayload(fields), expected_revision: expectedRevision };
        await documentWorkspaceMutation({
          action, route, scope: `document-workspace:${workspaceId}:plan:create`,
          path: `/document-workspace/workspaces/${encodeURIComponent(workspaceId)}/plans`, payload,
          onSuccess: async (result) => {
            const receipt = result.data && result.data.plan && typeof result.data.plan === "object" ? result.data.plan : null;
            if (!documentWorkspaceBoundaryIsSafe(result.data) || !receipt || !validDocumentPlanId(receipt.id) || String(receipt.workspace_id || "") !== workspaceId) {
              throw new Error("Máy chủ chưa trả receipt processing plan hợp lệ.");
            }
            await hydrateDocumentWorkspace();
            await hydrateDocumentWorkspaceDetail(workspaceId);
            toast(result.message || "Đã thêm processing plan riêng tư.");
          }
        });
        return;
      }
      if (action === "document-plan-update") {
        const workspaceId = String(fields.__documentWorkspaceId || documentWorkspaceIdFromPath(route)).trim();
        const planId = String(fields.__documentPlanId || "").trim();
        const expectedRevision = validDocumentWorkspaceRevision(fields.__documentPlanRevision);
        if (!validDocumentWorkspaceId(workspaceId) || !validDocumentPlanId(planId) || !expectedRevision) throw new Error("Mã hoặc revision processing plan không hợp lệ.");
        const payload = { ...documentPlanPayload(fields), expected_revision: expectedRevision };
        await documentWorkspaceMutation({
          action, route, scope: `document-workspace:${workspaceId}:plan:${planId}:update`, method: "PATCH",
          path: `/document-workspace/workspaces/${encodeURIComponent(workspaceId)}/plans/${encodeURIComponent(planId)}`, payload,
          onSuccess: async (result) => {
            if (!documentWorkspaceBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận revision processing plan an toàn.");
            await hydrateDocumentWorkspaceDetail(workspaceId);
            toast(result.message || "Đã lưu revision processing plan mới.");
          }
        });
        return;
      }
      if (action === "document-plan-archive" || action === "document-plan-restore") {
        const workspaceId = String(fields.__documentWorkspaceId || documentWorkspaceIdFromPath(route)).trim();
        const planId = String(fields.__documentPlanId || "").trim();
        const expectedRevision = validDocumentWorkspaceRevision(fields.__documentPlanRevision);
        if (!validDocumentWorkspaceId(workspaceId) || !validDocumentPlanId(planId) || !expectedRevision) throw new Error("Mã hoặc revision processing plan không hợp lệ.");
        const operation = action.replace("document-plan-", "");
        await documentWorkspaceMutation({
          action, route, scope: `document-workspace:${workspaceId}:plan:${planId}:${operation}`,
          path: `/document-workspace/workspaces/${encodeURIComponent(workspaceId)}/plans/${encodeURIComponent(planId)}/${encodeURIComponent(operation)}`,
          payload: { expected_revision: expectedRevision },
          onSuccess: async (result) => {
            if (!documentWorkspaceBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận trạng thái processing plan an toàn.");
            await hydrateDocumentWorkspace();
            await hydrateDocumentWorkspaceDetail(workspaceId);
            toast(result.message || "Đã cập nhật processing plan.");
          }
        });
        return;
      }
      if (action === "document-plan-restore-version") {
        const workspaceId = String(fields.__documentWorkspaceId || documentWorkspaceIdFromPath(route)).trim();
        const planId = String(fields.__documentPlanId || "").trim();
        const expectedRevision = validDocumentWorkspaceRevision(fields.__documentPlanRevision);
        const targetRevision = validDocumentWorkspaceRevision(fields.__documentPlanVersion);
        if (!validDocumentWorkspaceId(workspaceId) || !validDocumentPlanId(planId) || !expectedRevision || !targetRevision) throw new Error("Version hoặc revision processing plan không hợp lệ.");
        await documentWorkspaceMutation({
          action, route, scope: `document-workspace:${workspaceId}:plan:${planId}:restore-version:${targetRevision}`,
          path: `/document-workspace/workspaces/${encodeURIComponent(workspaceId)}/plans/${encodeURIComponent(planId)}/restore-version`, payload: { expected_revision: expectedRevision, target_revision: targetRevision },
          onSuccess: async (result) => {
            if (!documentWorkspaceBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận version processing plan an toàn.");
            await hydrateDocumentWorkspaceDetail(workspaceId);
            toast(result.message || "Đã khôi phục version processing plan thành revision mới.");
          }
        });
        return;
      }
      if (action === "document-plan-reorder") {
        const workspaceId = String(fields.__documentWorkspaceId || documentWorkspaceIdFromPath(route)).trim();
        const expectedRevision = validDocumentWorkspaceRevision(fields.__documentWorkspaceRevision);
        const planId = String(fields.__documentPlanId || "").trim();
        const direction = String(fields.__documentPlanDirection || "").trim().toLowerCase();
        if (!validDocumentWorkspaceId(workspaceId) || !expectedRevision || !validDocumentPlanId(planId) || !["up", "down"].includes(direction)) throw new Error("Yêu cầu sắp xếp processing plan không hợp lệ.");
        const workspaceDetail = base().documentWorkspaceDetail && typeof base().documentWorkspaceDetail === "object" ? base().documentWorkspaceDetail : {};
        const activePlans = Array.isArray(workspaceDetail.plans)
          ? workspaceDetail.plans.filter((item) => item && String(item.workspace_id || "") === workspaceId && String(item.state || "active") === "active" && validDocumentPlanId(item.id))
          : [];
        const index = activePlans.findIndex((item) => String(item.id) === planId);
        const target = direction === "up" ? index - 1 : index + 1;
        if (index < 0 || target < 0 || target >= activePlans.length) throw new Error("Không thể đổi thứ tự processing plan ở vị trí này.");
        const planIds = activePlans.map((item) => String(item.id));
        [planIds[index], planIds[target]] = [planIds[target], planIds[index]];
        await documentWorkspaceMutation({
          action, route, scope: `document-workspace:${workspaceId}:plans:reorder`,
          path: `/document-workspace/workspaces/${encodeURIComponent(workspaceId)}/plans/reorder`, payload: { expected_revision: expectedRevision, plan_ids: planIds },
          onSuccess: async (result) => {
            if (!documentWorkspaceBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận thứ tự processing plan an toàn.");
            await hydrateDocumentWorkspaceDetail(workspaceId);
            toast(result.message || "Đã cập nhật thứ tự processing plan.");
          }
        });
        return;
      }
      if (action === "image-studio-refresh") {
        const artboardId = imageArtboardIdFromPath(route);
        if (artboardId) await hydrateImageArtboard(artboardId);
        else await hydrateImageStudio();
        toast("Đã làm mới Image Creative Studio của Web account hiện tại.");
        return;
      }
      if (action === "image-artboard-create") {
        const payload = imageArtboardPayload(fields);
        await imageStudioMutation({
          action, route, scope: "image-studio:artboard:create", path: "/image-studio/artboards", payload,
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.artboard && typeof data.artboard === "object" ? data.artboard : null;
            const artboardId = receipt && validImageStudioArtboardId(receipt.id) ? String(receipt.id) : "";
            if (!imageStudioBoundaryIsSafe(data) || !artboardId || !validImageStudioRevision(receipt.revision)) {
              throw new Error("Máy chủ chưa trả receipt artboard Web-native hợp lệ.");
            }
            await hydrateImageStudio();
            toast(result.message || "Đã tạo artboard riêng tư.");
            window.location.assign(`/image-studio/${encodeURIComponent(artboardId)}`);
          }
        });
        return;
      }
      if (action === "image-artboard-update") {
        const artboardId = String(detail.imageArtboardId || "").trim();
        const expectedRevision = validImageStudioRevision(detail.imageArtboardRevision);
        if (!validImageStudioArtboardId(artboardId) || !expectedRevision) throw new Error("Mã hoặc revision artboard không hợp lệ.");
        const payload = { ...imageArtboardPayload(fields), expected_revision: expectedRevision };
        await imageStudioMutation({
          action, route, scope: `image-studio:artboard:${artboardId}:update`, method: "PATCH",
          path: `/image-studio/artboards/${encodeURIComponent(artboardId)}`, payload,
          onSuccess: async (result) => {
            if (!imageStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận revision artboard an toàn.");
            await hydrateImageStudio();
            await hydrateImageArtboard(artboardId);
            toast(result.message || "Đã lưu revision artboard mới.");
          }
        });
        return;
      }
      if (action === "image-artboard-state") {
        const artboardId = String(detail.imageArtboardId || "").trim();
        const expectedRevision = validImageStudioRevision(detail.imageArtboardRevision);
        const state = String(detail.imageArtboardState || "").trim().toLowerCase();
        if (!validImageStudioArtboardId(artboardId) || !expectedRevision || !IMAGE_STUDIO_STATES.has(state)) throw new Error("Trạng thái hoặc revision artboard không hợp lệ.");
        const current = base().imageArtboardDetail && base().imageArtboardDetail.artboard;
        const currentState = current && String(current.id || "") === artboardId ? String(current.state || "") : "";
        if (currentState === "archived" && state !== "draft") throw new Error("Artboard đã archive chỉ có thể được khôi phục về Draft.");
        if (currentState === "approved" && !["draft", "archived"].includes(state)) throw new Error("Artboard self-review xong cần về Draft trước khi thay đổi review.");
        await imageStudioMutation({
          action, route, scope: `image-studio:artboard:${artboardId}:state:${state}`,
          path: `/image-studio/artboards/${encodeURIComponent(artboardId)}/lifecycle`, payload: { state, expected_revision: expectedRevision },
          onSuccess: async (result) => {
            const receipt = result.data && result.data.artboard && typeof result.data.artboard === "object" ? result.data.artboard : null;
            if (!imageStudioBoundaryIsSafe(result.data) || !receipt || !validImageStudioRevision(receipt.revision)) throw new Error("Máy chủ chưa xác nhận trạng thái artboard an toàn.");
            await hydrateImageStudio();
            await hydrateImageArtboard(artboardId);
            toast(result.message || "Đã cập nhật trạng thái self-review.");
          }
        });
        return;
      }
      if (action === "image-artboard-restore-version") {
        const artboardId = String(detail.imageArtboardId || "").trim();
        const expectedRevision = validImageStudioRevision(detail.imageArtboardRevision);
        const targetRevision = validImageStudioRevision(detail.imageArtboardVersion);
        if (!validImageStudioArtboardId(artboardId) || !expectedRevision || !targetRevision) throw new Error("Version hoặc revision artboard không hợp lệ.");
        await imageStudioMutation({
          action, route, scope: `image-studio:artboard:${artboardId}:restore-version:${targetRevision}`,
          path: `/image-studio/artboards/${encodeURIComponent(artboardId)}/restore-version`, payload: { expected_revision: expectedRevision, target_revision: targetRevision },
          onSuccess: async (result) => {
            if (!imageStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận version artboard an toàn.");
            await hydrateImageStudio();
            await hydrateImageArtboard(artboardId);
            toast(result.message || "Đã khôi phục version artboard thành revision mới.");
          }
        });
        return;
      }
      if (action === "image-direction-create") {
        const artboardId = String(detail.imageArtboardId || "").trim();
        const expectedRevision = validImageStudioRevision(detail.imageArtboardRevision);
        if (!validImageStudioArtboardId(artboardId) || !expectedRevision) throw new Error("Mã hoặc revision artboard không hợp lệ.");
        const payload = { ...imageDirectionPayload(fields), expected_revision: expectedRevision };
        await imageStudioMutation({
          action, route, scope: `image-studio:artboard:${artboardId}:direction:create`,
          path: `/image-studio/artboards/${encodeURIComponent(artboardId)}/directions`, payload,
          onSuccess: async (result) => {
            const receipt = result.data && result.data.direction && typeof result.data.direction === "object" ? result.data.direction : null;
            if (!imageStudioBoundaryIsSafe(result.data) || !receipt || !validImageStudioDirectionId(receipt.id) || String(receipt.artboard_id || "") !== artboardId) {
              throw new Error("Máy chủ chưa trả receipt biến thể direction hợp lệ.");
            }
            await hydrateImageStudio();
            await hydrateImageArtboard(artboardId);
            toast(result.message || "Đã thêm biến thể direction riêng tư.");
          }
        });
        return;
      }
      if (action === "image-direction-update") {
        const artboardId = String(detail.imageArtboardId || "").trim();
        const directionId = String(detail.imageDirectionId || "").trim();
        const expectedRevision = validImageStudioRevision(detail.imageDirectionRevision);
        if (!validImageStudioArtboardId(artboardId) || !validImageStudioDirectionId(directionId) || !expectedRevision) throw new Error("Mã hoặc revision biến thể direction không hợp lệ.");
        const payload = { ...imageDirectionPayload(fields), expected_revision: expectedRevision };
        await imageStudioMutation({
          action, route, scope: `image-studio:artboard:${artboardId}:direction:${directionId}:update`, method: "PATCH",
          path: `/image-studio/artboards/${encodeURIComponent(artboardId)}/directions/${encodeURIComponent(directionId)}`, payload,
          onSuccess: async (result) => {
            if (!imageStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận revision biến thể direction an toàn.");
            await hydrateImageArtboard(artboardId);
            toast(result.message || "Đã lưu revision biến thể direction mới.");
          }
        });
        return;
      }
      if (action === "image-direction-archive" || action === "image-direction-restore") {
        const artboardId = String(detail.imageArtboardId || "").trim();
        const directionId = String(detail.imageDirectionId || "").trim();
        const expectedRevision = validImageStudioRevision(detail.imageDirectionRevision);
        if (!validImageStudioArtboardId(artboardId) || !validImageStudioDirectionId(directionId) || !expectedRevision) throw new Error("Mã hoặc revision biến thể direction không hợp lệ.");
        const operation = action.replace("image-direction-", "");
        await imageStudioMutation({
          action, route, scope: `image-studio:artboard:${artboardId}:direction:${directionId}:${operation}`,
          path: `/image-studio/artboards/${encodeURIComponent(artboardId)}/directions/${encodeURIComponent(directionId)}/${encodeURIComponent(operation)}`,
          payload: { expected_revision: expectedRevision },
          onSuccess: async (result) => {
            if (!imageStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận trạng thái biến thể direction an toàn.");
            await hydrateImageStudio();
            await hydrateImageArtboard(artboardId);
            toast(result.message || "Đã cập nhật biến thể direction.");
          }
        });
        return;
      }
      if (action === "image-direction-restore-version") {
        const artboardId = String(detail.imageArtboardId || "").trim();
        const directionId = String(detail.imageDirectionId || "").trim();
        const expectedRevision = validImageStudioRevision(detail.imageDirectionRevision);
        const targetRevision = validImageStudioRevision(detail.imageDirectionVersion);
        if (!validImageStudioArtboardId(artboardId) || !validImageStudioDirectionId(directionId) || !expectedRevision || !targetRevision) throw new Error("Version hoặc revision biến thể direction không hợp lệ.");
        await imageStudioMutation({
          action, route, scope: `image-studio:artboard:${artboardId}:direction:${directionId}:restore-version:${targetRevision}`,
          path: `/image-studio/artboards/${encodeURIComponent(artboardId)}/directions/${encodeURIComponent(directionId)}/restore-version`,
          payload: { expected_revision: expectedRevision, target_revision: targetRevision },
          onSuccess: async (result) => {
            if (!imageStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận version biến thể direction an toàn.");
            await hydrateImageArtboard(artboardId);
            toast(result.message || "Đã khôi phục version biến thể direction thành revision mới.");
          }
        });
        return;
      }
      if (action === "subtitle-studio-refresh") {
        const projectId = subtitleProjectIdFromPath(route);
        if (projectId) await hydrateSubtitleProject(projectId);
        else await hydrateSubtitleStudio();
        toast("Đã làm mới Subtitle & Transcript Workspace của Web account hiện tại.");
        return;
      }
      if (action === "subtitle-project-create") {
        const payload = subtitleProjectPayload(fields);
        await subtitleStudioMutation({
          action, route, scope: "subtitle-studio:project:create", path: "/subtitle-studio/projects", payload,
          onSuccess: async (result) => {
            const data = result.data && typeof result.data === "object" ? result.data : {};
            const receipt = data.project && typeof data.project === "object" ? data.project : null;
            const projectId = receipt && validSubtitleStudioProjectId(receipt.id) ? String(receipt.id) : "";
            if (!subtitleStudioBoundaryIsSafe(data) || !projectId || !validSubtitleStudioRevision(receipt.revision)) {
              throw new Error("Máy chủ chưa trả receipt transcript project Web-native hợp lệ.");
            }
            await hydrateSubtitleStudio();
            toast(result.message || "Đã tạo transcript project riêng tư.");
            window.location.assign(`/subtitle-studio/${encodeURIComponent(projectId)}`);
          }
        });
        return;
      }
      if (action === "subtitle-project-update") {
        const projectId = String(detail.subtitleProjectId || "").trim();
        const expectedRevision = validSubtitleStudioRevision(detail.subtitleProjectRevision);
        if (!validSubtitleStudioProjectId(projectId) || !expectedRevision) throw new Error("Mã hoặc revision transcript project không hợp lệ.");
        const payload = { ...subtitleProjectPayload(fields), expected_revision: expectedRevision };
        await subtitleStudioMutation({
          action, route, scope: `subtitle-studio:project:${projectId}:update`, method: "PATCH",
          path: `/subtitle-studio/projects/${encodeURIComponent(projectId)}`, payload,
          onSuccess: async (result) => {
            if (!subtitleStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận revision transcript project an toàn.");
            await hydrateSubtitleStudio();
            await hydrateSubtitleProject(projectId);
            toast(result.message || "Đã lưu revision transcript project mới.");
          }
        });
        return;
      }
      if (action === "subtitle-project-state") {
        const projectId = String(detail.subtitleProjectId || "").trim();
        const expectedRevision = validSubtitleStudioRevision(detail.subtitleProjectRevision);
        const state = String(detail.subtitleProjectState || "").trim().toLowerCase();
        if (!validSubtitleStudioProjectId(projectId) || !expectedRevision || !SUBTITLE_STUDIO_PROJECT_STATES.has(state)) throw new Error("Trạng thái hoặc revision transcript project không hợp lệ.");
        const current = base().subtitleProjectDetail && base().subtitleProjectDetail.project;
        const currentState = current && String(current.id || "") === projectId ? String(current.state || "") : "";
        if (currentState === "archived" && state !== "draft") throw new Error("Project đã archive chỉ có thể được khôi phục về Draft.");
        if (currentState === "approved" && !["draft", "archived"].includes(state)) throw new Error("Project self-review xong cần về Draft trước khi thay đổi review.");
        await subtitleStudioMutation({
          action, route, scope: `subtitle-studio:project:${projectId}:state:${state}`,
          path: `/subtitle-studio/projects/${encodeURIComponent(projectId)}/lifecycle`, payload: { state, expected_revision: expectedRevision },
          onSuccess: async (result) => {
            const receipt = result.data && result.data.project && typeof result.data.project === "object" ? result.data.project : null;
            if (!subtitleStudioBoundaryIsSafe(result.data) || !receipt || !validSubtitleStudioRevision(receipt.revision)) throw new Error("Máy chủ chưa xác nhận trạng thái project an toàn.");
            await hydrateSubtitleStudio();
            await hydrateSubtitleProject(projectId);
            toast(result.message || "Đã cập nhật trạng thái self-review.");
          }
        });
        return;
      }
      if (action === "subtitle-project-restore-version") {
        const projectId = String(detail.subtitleProjectId || "").trim();
        const expectedRevision = validSubtitleStudioRevision(detail.subtitleProjectRevision);
        const targetRevision = validSubtitleStudioRevision(detail.subtitleProjectVersion);
        if (!validSubtitleStudioProjectId(projectId) || !expectedRevision || !targetRevision) throw new Error("Version hoặc revision transcript project không hợp lệ.");
        await subtitleStudioMutation({
          action, route, scope: `subtitle-studio:project:${projectId}:restore-version:${targetRevision}`,
          path: `/subtitle-studio/projects/${encodeURIComponent(projectId)}/restore-version`, payload: { expected_revision: expectedRevision, target_revision: targetRevision },
          onSuccess: async (result) => {
            if (!subtitleStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận version transcript project an toàn.");
            await hydrateSubtitleStudio();
            await hydrateSubtitleProject(projectId);
            toast(result.message || "Đã khôi phục version transcript project thành revision mới.");
          }
        });
        return;
      }
      if (action === "subtitle-cue-create") {
        const projectId = String(detail.subtitleProjectId || "").trim();
        const expectedRevision = validSubtitleStudioRevision(detail.subtitleProjectRevision);
        if (!validSubtitleStudioProjectId(projectId) || !expectedRevision) throw new Error("Mã hoặc revision transcript project không hợp lệ.");
        const payload = { ...subtitleCuePayload(fields), expected_revision: expectedRevision };
        await subtitleStudioMutation({
          action, route, scope: `subtitle-studio:project:${projectId}:cue:create`,
          path: `/subtitle-studio/projects/${encodeURIComponent(projectId)}/cues`, payload,
          onSuccess: async (result) => {
            const receipt = result.data && result.data.cue && typeof result.data.cue === "object" ? result.data.cue : null;
            if (!subtitleStudioBoundaryIsSafe(result.data) || !receipt || !validSubtitleStudioCueId(receipt.id) || String(receipt.project_id || "") !== projectId) {
              throw new Error("Máy chủ chưa trả receipt cue hợp lệ.");
            }
            await hydrateSubtitleStudio();
            await hydrateSubtitleProject(projectId);
            toast(result.message || "Đã thêm cue riêng tư.");
          }
        });
        return;
      }
      if (action === "subtitle-cue-import") {
        const projectId = String(detail.subtitleProjectId || "").trim();
        const expectedRevision = validSubtitleStudioRevision(detail.subtitleProjectRevision);
        if (!validSubtitleStudioProjectId(projectId) || !expectedRevision) throw new Error("Mã hoặc revision transcript project không hợp lệ.");
        const payload = { ...subtitleTextImportPayload(fields), expected_revision: expectedRevision };
        await subtitleStudioMutation({
          action, route, scope: `subtitle-studio:project:${projectId}:cue-import`,
          path: `/subtitle-studio/projects/${encodeURIComponent(projectId)}/import`, payload,
          onSuccess: async (result) => {
            if (!subtitleStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận text import Subtitle Studio an toàn.");
            await hydrateSubtitleStudio();
            await hydrateSubtitleProject(projectId);
            toast(result.message || "Đã archive cue active cũ và thay bằng cue parse từ văn bản tác giả; history vẫn được giữ.");
          }
        });
        return;
      }
      if (action === "subtitle-text-export") {
        const projectId = String(detail.subtitleProjectId || "").trim();
        const format = String(detail.subtitleExportFormat || "").trim().toLowerCase();
        if (!validSubtitleStudioProjectId(projectId) || !SUBTITLE_STUDIO_FORMATS.has(format)) throw new Error("Mã project hoặc chuẩn text subtitle không hợp lệ.");
        setActionBusy(action, route, true);
        try {
          const result = await api(`/subtitle-studio/projects/${encodeURIComponent(projectId)}/export?format=${encodeURIComponent(format)}`);
          const data = result.data && typeof result.data === "object" ? result.data : {};
          if (!subtitleStudioBoundaryIsSafe(data) || String(data.format || "").toLowerCase() !== format || typeof data.text !== "string") {
            throw new Error("Máy chủ chưa trả văn bản subtitle an toàn để sao chép.");
          }
          await copySubtitleStudioText(data.text);
          toast(result.message || `Đã sao chép ${format.toUpperCase()} text từ cue authoring. Không có file hoặc delivery được tạo.`);
        } finally {
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "subtitle-cue-update") {
        const projectId = String(detail.subtitleProjectId || "").trim();
        const cueId = String(detail.subtitleCueId || "").trim();
        const expectedRevision = validSubtitleStudioRevision(detail.subtitleCueRevision);
        if (!validSubtitleStudioProjectId(projectId) || !validSubtitleStudioCueId(cueId) || !expectedRevision) throw new Error("Mã hoặc revision cue không hợp lệ.");
        const payload = { ...subtitleCuePayload(fields), expected_revision: expectedRevision };
        await subtitleStudioMutation({
          action, route, scope: `subtitle-studio:project:${projectId}:cue:${cueId}:update`, method: "PATCH",
          path: `/subtitle-studio/projects/${encodeURIComponent(projectId)}/cues/${encodeURIComponent(cueId)}`, payload,
          onSuccess: async (result) => {
            if (!subtitleStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận revision cue an toàn.");
            await hydrateSubtitleProject(projectId);
            toast(result.message || "Đã lưu revision cue mới.");
          }
        });
        return;
      }
      if (action === "subtitle-cue-archive" || action === "subtitle-cue-restore") {
        const projectId = String(detail.subtitleProjectId || "").trim();
        const cueId = String(detail.subtitleCueId || "").trim();
        const expectedRevision = validSubtitleStudioRevision(detail.subtitleCueRevision);
        if (!validSubtitleStudioProjectId(projectId) || !validSubtitleStudioCueId(cueId) || !expectedRevision) throw new Error("Mã hoặc revision cue không hợp lệ.");
        const operation = action.replace("subtitle-cue-", "");
        await subtitleStudioMutation({
          action, route, scope: `subtitle-studio:project:${projectId}:cue:${cueId}:${operation}`,
          path: `/subtitle-studio/projects/${encodeURIComponent(projectId)}/cues/${encodeURIComponent(cueId)}/${encodeURIComponent(operation)}`,
          payload: { expected_revision: expectedRevision },
          onSuccess: async (result) => {
            if (!subtitleStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận trạng thái cue an toàn.");
            await hydrateSubtitleStudio();
            await hydrateSubtitleProject(projectId);
            toast(result.message || "Đã cập nhật cue.");
          }
        });
        return;
      }
      if (action === "subtitle-cue-restore-version") {
        const projectId = String(detail.subtitleProjectId || "").trim();
        const cueId = String(detail.subtitleCueId || "").trim();
        const expectedRevision = validSubtitleStudioRevision(detail.subtitleCueRevision);
        const targetRevision = validSubtitleStudioRevision(detail.subtitleCueVersion);
        if (!validSubtitleStudioProjectId(projectId) || !validSubtitleStudioCueId(cueId) || !expectedRevision || !targetRevision) throw new Error("Version hoặc revision cue không hợp lệ.");
        await subtitleStudioMutation({
          action, route, scope: `subtitle-studio:project:${projectId}:cue:${cueId}:restore-version:${targetRevision}`,
          path: `/subtitle-studio/projects/${encodeURIComponent(projectId)}/cues/${encodeURIComponent(cueId)}/restore-version`,
          payload: { expected_revision: expectedRevision, target_revision: targetRevision },
          onSuccess: async (result) => {
            if (!subtitleStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận version cue an toàn.");
            await hydrateSubtitleProject(projectId);
            toast(result.message || "Đã khôi phục version cue thành revision mới.");
          }
        });
        return;
      }
      if (action === "subtitle-cue-reorder") {
        const projectId = String(detail.subtitleProjectId || "").trim();
        const expectedRevision = validSubtitleStudioRevision(detail.subtitleProjectRevision);
        const cueId = String(detail.subtitleCueId || "").trim();
        const direction = String(detail.subtitleCueDirection || "").trim().toLowerCase();
        if (!validSubtitleStudioProjectId(projectId) || !expectedRevision || !validSubtitleStudioCueId(cueId) || !["up", "down"].includes(direction)) throw new Error("Yêu cầu sắp xếp cue không hợp lệ.");
        const projectDetail = base().subtitleProjectDetail && typeof base().subtitleProjectDetail === "object" ? base().subtitleProjectDetail : {};
        const activeCues = Array.isArray(projectDetail.cues)
          ? projectDetail.cues.filter((item) => item && String(item.project_id || "") === projectId && String(item.state || "active") === "active" && validSubtitleStudioCueId(item.id))
          : [];
        const index = activeCues.findIndex((item) => String(item.id) === cueId);
        const target = direction === "up" ? index - 1 : index + 1;
        if (index < 0 || target < 0 || target >= activeCues.length) throw new Error("Không thể đổi thứ tự cue ở vị trí này.");
        const cueIds = activeCues.map((item) => String(item.id));
        [cueIds[index], cueIds[target]] = [cueIds[target], cueIds[index]];
        await subtitleStudioMutation({
          action, route, scope: `subtitle-studio:project:${projectId}:cues:reorder`,
          path: `/subtitle-studio/projects/${encodeURIComponent(projectId)}/cues/reorder`, payload: { expected_revision: expectedRevision, cue_ids: cueIds },
          onSuccess: async (result) => {
            if (!subtitleStudioBoundaryIsSafe(result.data)) throw new Error("Máy chủ chưa xác nhận thứ tự cue an toàn.");
            await hydrateSubtitleProject(projectId);
            toast(result.message || "Đã cập nhật thứ tự cue.");
          }
        });
        return;
      }
      if (action === "voice-studio-filter" || action === "voice-studio-filter-clear") {
        const filter = action === "voice-studio-filter-clear"
          ? { q: "", tag: "", state: "all" }
          : voiceStudioFilterPayload(fields);
        await hydrateVoiceStudio(filter);
        toast(filter.q || filter.tag || filter.state !== "all" ? "Đã áp dụng bộ lọc Voice Studio." : "Đã hiển thị tất cả Voice Vault riêng tư.");
        return;
      }
      if (action === "voice-studio-refresh") {
        const vaultId = voiceVaultIdFromPath(route);
        if (vaultId) await hydrateVoiceVault(vaultId);
        else await hydrateVoiceStudio();
        toast("Đã làm mới Voice Studio của Web account hiện tại.");
        return;
      }
      if (action === "voice-vault-create") {
        const payload = voiceVaultPayload(fields);
        await voiceStudioMutation({
          action, route, scope: "voice-studio:vault:create", path: "/voice-studio/vaults", payload,
          onSuccess: async (result) => {
            const receipt = result.data && result.data.vault && typeof result.data.vault === "object" ? result.data.vault : null;
            const vaultId = receipt && validVoiceStudioVaultId(receipt.id) ? String(receipt.id) : "";
            if (!vaultId || !validVoiceStudioRevision(receipt.revision) || result.data.provider_called !== false || result.data.audio_created !== false) {
              throw new Error("Máy chủ chưa trả receipt Voice Vault Web-native hợp lệ.");
            }
            await hydrateVoiceStudio();
            toast(result.message || "Đã tạo Voice Vault Web-native.");
            window.location.assign(`/voice-studio/${encodeURIComponent(vaultId)}`);
          }
        });
        return;
      }
      if (action === "voice-vault-update") {
        const vaultId = String(detail.voiceVaultId || "").trim();
        const expectedRevision = validVoiceStudioRevision(detail.voiceVaultRevision);
        if (!validVoiceStudioVaultId(vaultId) || !expectedRevision) throw new Error("Mã hoặc revision Voice Vault không hợp lệ.");
        const payload = { ...voiceVaultPayload(fields), expected_revision: expectedRevision };
        await voiceStudioMutation({
          action, route, scope: `voice-studio:vault:${vaultId}:update`, method: "PATCH",
          path: `/voice-studio/vaults/${encodeURIComponent(vaultId)}`, payload,
          onSuccess: async (result) => {
            if (!result.data || result.data.provider_called !== false || result.data.audio_created !== false) throw new Error("Máy chủ chưa xác nhận revision Voice Vault an toàn.");
            await hydrateVoiceStudio();
            await hydrateVoiceVault(vaultId);
            toast(result.message || "Đã lưu revision Voice Vault mới.");
          }
        });
        return;
      }
      if (["voice-vault-archive", "voice-vault-restore", "voice-vault-duplicate", "voice-vault-restore-version"].includes(action)) {
        const vaultId = String(detail.voiceVaultId || "").trim();
        const expectedRevision = validVoiceStudioRevision(detail.voiceVaultRevision);
        if (!validVoiceStudioVaultId(vaultId) || !expectedRevision) throw new Error("Mã hoặc revision Voice Vault không hợp lệ.");
        const operation = action.replace("voice-vault-", "");
        const targetRevision = action === "voice-vault-restore-version" ? validVoiceStudioRevision(detail.voiceVaultVersion) : 0;
        if (action === "voice-vault-restore-version" && !targetRevision) throw new Error("Phiên bản Voice Vault cần khôi phục không hợp lệ.");
        const payload = action === "voice-vault-restore-version"
          ? { expected_revision: expectedRevision, target_revision: targetRevision }
          : { expected_revision: expectedRevision };
        const path = action === "voice-vault-restore-version"
          ? `/voice-studio/vaults/${encodeURIComponent(vaultId)}/restore-version`
          : `/voice-studio/vaults/${encodeURIComponent(vaultId)}/${encodeURIComponent(operation)}`;
        const scope = `voice-studio:vault:${vaultId}:${operation}${targetRevision ? `:${targetRevision}` : ""}`;
        await voiceStudioMutation({
          action, route, scope, path, payload,
          onSuccess: async (result) => {
            const receipt = result.data && result.data.vault && typeof result.data.vault === "object" ? result.data.vault : null;
            if (!receipt || result.data.provider_called !== false || result.data.audio_created !== false) throw new Error("Máy chủ chưa xác nhận trạng thái Voice Vault an toàn.");
            const createdId = action === "voice-vault-duplicate" && validVoiceStudioVaultId(receipt.id) ? String(receipt.id) : "";
            if (action === "voice-vault-duplicate" && !createdId) throw new Error("Máy chủ chưa trả bản sao Voice Vault hợp lệ.");
            await hydrateVoiceStudio();
            if (createdId) {
              toast(result.message || "Đã nhân bản Voice Vault riêng tư.");
              window.location.assign(`/voice-studio/${encodeURIComponent(createdId)}`);
              return;
            }
            await hydrateVoiceVault(vaultId);
            toast(result.message || "Đã cập nhật Voice Vault.");
          }
        });
        return;
      }
      if (action === "voice-vault-compose") {
        const vaultId = String(detail.voiceVaultId || "").trim();
        const expectedRevision = validVoiceStudioRevision(detail.voiceVaultRevision);
        if (!validVoiceStudioVaultId(vaultId) || !expectedRevision) throw new Error("Mã hoặc revision Voice Vault không hợp lệ.");
        await voiceStudioMutation({
          action, route, scope: `voice-studio:vault:${vaultId}:compose`,
          path: `/voice-studio/vaults/${encodeURIComponent(vaultId)}/compose`, payload: { expected_revision: expectedRevision },
          onSuccess: async (result) => {
            const output = result.data && typeof result.data === "object" ? result.data : {};
            const ids = Array.isArray(output.script_ids) ? output.script_ids.filter(validVoiceStudioScriptId) : [];
            if (output.execution !== "local_deterministic_draft_only" || output.provider_called !== false || output.audio_created !== false || ids.length !== 3) {
              throw new Error("Máy chủ chưa trả 3 khung script cục bộ hợp lệ.");
            }
            await hydrateVoiceStudio();
            await hydrateVoiceVault(vaultId);
            toast(result.message || "Đã tạo 3 khung script cục bộ để biên tập.");
          }
        });
        return;
      }
      if (action === "voice-script-create") {
        const vaultId = String(detail.voiceVaultId || "").trim();
        // Creating a script is guarded by the enclosing vault revision, not
        // an invented browser-side script revision.
        const expectedRevision = validVoiceStudioRevision(detail.voiceVaultRevision);
        if (!validVoiceStudioVaultId(vaultId) || !expectedRevision) throw new Error("Mã hoặc revision Voice Vault không hợp lệ.");
        const payload = { ...voiceScriptPayload(fields), expected_revision: expectedRevision };
        await voiceStudioMutation({
          action, route, scope: `voice-studio:vault:${vaultId}:script:create`,
          path: `/voice-studio/vaults/${encodeURIComponent(vaultId)}/scripts`, payload,
          onSuccess: async (result) => {
            const receipt = result.data && result.data.script && typeof result.data.script === "object" ? result.data.script : null;
            if (!receipt || !validVoiceStudioScriptId(receipt.id) || String(receipt.vault_id || "") !== vaultId || receipt.source_kind !== "manual" || result.data.provider_called !== false || result.data.audio_created !== false) {
              throw new Error("Máy chủ chưa trả receipt script Voice Studio hợp lệ.");
            }
            await hydrateVoiceStudio();
            await hydrateVoiceVault(vaultId);
            toast(result.message || "Đã thêm script riêng tư vào Voice Vault.");
          }
        });
        return;
      }
      if (action === "voice-script-update") {
        const vaultId = String(detail.voiceVaultId || "").trim();
        const scriptId = String(detail.voiceScriptId || "").trim();
        const expectedRevision = validVoiceStudioRevision(detail.voiceScriptRevision);
        if (!validVoiceStudioVaultId(vaultId) || !validVoiceStudioScriptId(scriptId) || !expectedRevision) throw new Error("Mã hoặc revision script Voice Studio không hợp lệ.");
        const payload = { ...voiceScriptPayload(fields), expected_revision: expectedRevision };
        await voiceStudioMutation({
          action, route, scope: `voice-studio:vault:${vaultId}:script:${scriptId}:update`, method: "PATCH",
          path: `/voice-studio/vaults/${encodeURIComponent(vaultId)}/scripts/${encodeURIComponent(scriptId)}`, payload,
          onSuccess: async (result) => {
            if (!result.data || result.data.provider_called !== false || result.data.audio_created !== false) throw new Error("Máy chủ chưa xác nhận revision script an toàn.");
            await hydrateVoiceVault(vaultId);
            toast(result.message || "Đã lưu revision script mới.");
          }
        });
        return;
      }
      if (["voice-script-archive", "voice-script-restore", "voice-script-duplicate", "voice-script-restore-version"].includes(action)) {
        const vaultId = String(detail.voiceVaultId || "").trim();
        const scriptId = String(detail.voiceScriptId || "").trim();
        const expectedRevision = validVoiceStudioRevision(detail.voiceScriptRevision);
        if (!validVoiceStudioVaultId(vaultId) || !validVoiceStudioScriptId(scriptId) || !expectedRevision) throw new Error("Mã hoặc revision script Voice Studio không hợp lệ.");
        const operation = action.replace("voice-script-", "");
        const targetRevision = action === "voice-script-restore-version" ? validVoiceStudioRevision(detail.voiceScriptVersion) : 0;
        if (action === "voice-script-restore-version" && !targetRevision) throw new Error("Phiên bản script cần khôi phục không hợp lệ.");
        const payload = action === "voice-script-restore-version"
          ? { expected_revision: expectedRevision, target_revision: targetRevision }
          : { expected_revision: expectedRevision };
        const path = action === "voice-script-restore-version"
          ? `/voice-studio/vaults/${encodeURIComponent(vaultId)}/scripts/${encodeURIComponent(scriptId)}/restore-version`
          : `/voice-studio/vaults/${encodeURIComponent(vaultId)}/scripts/${encodeURIComponent(scriptId)}/${encodeURIComponent(operation)}`;
        const scope = `voice-studio:vault:${vaultId}:script:${scriptId}:${operation}${targetRevision ? `:${targetRevision}` : ""}`;
        await voiceStudioMutation({
          action, route, scope, path, payload,
          onSuccess: async (result) => {
            const receipt = result.data && result.data.script && typeof result.data.script === "object" ? result.data.script : null;
            if (!receipt || result.data.provider_called !== false || result.data.audio_created !== false) throw new Error("Máy chủ chưa xác nhận trạng thái script an toàn.");
            if (action === "voice-script-duplicate" && (!validVoiceStudioScriptId(receipt.id) || String(receipt.vault_id || "") !== vaultId)) {
              throw new Error("Máy chủ chưa trả bản sao script hợp lệ.");
            }
            await hydrateVoiceVault(vaultId);
            toast(result.message || "Đã cập nhật script riêng tư.");
          }
        });
        return;
      }
      if (action === "voice-script-cue-sheet") {
        const vaultId = String(detail.voiceVaultId || "").trim();
        const scriptId = String(detail.voiceScriptId || "").trim();
        if (!validVoiceStudioVaultId(vaultId) || !validVoiceStudioScriptId(scriptId)) throw new Error("Mã Voice Vault hoặc script không hợp lệ.");
        setActionBusy(action, route, true);
        try {
          await hydrateVoiceCueSheet(vaultId, scriptId);
          toast("Đã tạo cue-sheet cục bộ để review script; không có audio hoặc preview.");
        } finally {
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "support-cases-filter") {
        const filter = supportCaseFilterPayload(fields);
        await hydrateSupportDesk(filter);
        toast("Đã cập nhật danh sách yêu cầu Web.");
        return;
      }
      if (action === "support-cases-refresh") {
        const caseId = supportCaseIdFromPath(route);
        if (caseId) await hydrateSupportCase(caseId);
        else await hydrateSupportDesk();
        toast("Đã làm mới Web Support Desk.");
        return;
      }
      if (action === "support-case-create") {
        const payload = supportCreatePayload(fields);
        const scope = "support:case:create";
        const submission = acquireSubmission(scope, JSON.stringify(payload));
        if (!submission) {
          toast("Yêu cầu đang được gửi. Vui lòng chờ máy chủ xác nhận.", "error");
          return;
        }
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api("/support/cases", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, idempotency_key: submission.key })
          });
          acknowledged = true;
          const caseItem = result.data && result.data.case && typeof result.data.case === "object" ? result.data.case : null;
          const caseId = caseItem && validSupportCaseId(caseItem.id) ? String(caseItem.id) : "";
          toast(result.message || "Đã ghi nhận yêu cầu trong Web Support Desk.");
          if (caseId) window.location.assign(`/tickets/${encodeURIComponent(caseId)}`);
          else await hydrateSupportDesk();
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
      if (action === "support-case-reply") {
        const caseId = String(detail.supportCaseId || "").trim();
        const revision = validSupportRevision(detail.supportCaseRevision);
        if (!validSupportCaseId(caseId) || !revision) throw new Error("Mã hoặc phiên bản yêu cầu Support Desk không hợp lệ.");
        const payload = supportReplyPayload(fields);
        const scope = `support:case:${caseId}:reply`;
        const submission = acquireSubmission(scope, JSON.stringify({ ...payload, revision }));
        if (!submission) return;
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api(`/support/cases/${encodeURIComponent(caseId)}/reply`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, expected_revision: revision, idempotency_key: submission.key })
          });
          acknowledged = true;
          await hydrateSupportCase(caseId);
          toast(result.message || "Đã thêm phản hồi trong Web Support Desk.");
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
      if (action === "support-case-close" || action === "support-case-reopen") {
        const caseId = String(detail.supportCaseId || "").trim();
        const revision = validSupportRevision(detail.supportCaseRevision);
        if (!validSupportCaseId(caseId) || !revision) throw new Error("Mã hoặc phiên bản yêu cầu Support Desk không hợp lệ.");
        const operation = action === "support-case-close" ? "close" : "reopen";
        const scope = `support:case:${caseId}:${operation}`;
        const submission = acquireSubmission(scope, String(revision));
        if (!submission) return;
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api(`/support/cases/${encodeURIComponent(caseId)}/${operation}`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ expected_revision: revision, confirm: true, idempotency_key: submission.key })
          });
          acknowledged = true;
          await hydrateSupportCase(caseId);
          toast(result.message || "Đã cập nhật trạng thái yêu cầu Web.");
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
      if (action === "support-admin-cases-filter") {
        const filter = supportCaseFilterPayload(fields);
        await hydrateSupportAdmin(filter);
        toast("Đã cập nhật hàng đợi Support Desk.");
        return;
      }
      if (action === "support-admin-cases-refresh") {
        const caseId = supportAdminCaseIdFromPath(route);
        if (caseId) await hydrateSupportAdminCase(caseId);
        else await hydrateSupportAdmin();
        toast("Đã làm mới hàng đợi Support Desk.");
        return;
      }
      if (action === "support-admin-case-reply") {
        const caseId = String(detail.supportCaseId || "").trim();
        const revision = validSupportRevision(detail.supportCaseRevision);
        if (!validSupportCaseId(caseId) || !revision) throw new Error("Mã hoặc phiên bản case Support Desk không hợp lệ.");
        const payload = supportAdminReplyPayload(fields);
        const scope = `support:admin:case:${caseId}:reply`;
        const submission = acquireSubmission(scope, JSON.stringify({ ...payload, revision }));
        if (!submission) return;
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api(`/support/admin/cases/${encodeURIComponent(caseId)}/reply`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, expected_revision: revision, confirm: true, idempotency_key: submission.key })
          });
          acknowledged = true;
          await hydrateSupportAdminCase(caseId);
          toast(result.message || "Đã lưu phản hồi Support Desk.");
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
      if (action === "support-admin-case-update") {
        const caseId = String(detail.supportCaseId || "").trim();
        const revision = validSupportRevision(detail.supportCaseRevision);
        if (!validSupportCaseId(caseId) || !revision) throw new Error("Mã hoặc phiên bản case Support Desk không hợp lệ.");
        const payload = supportAdminUpdatePayload(fields);
        const scope = `support:admin:case:${caseId}:update`;
        const submission = acquireSubmission(scope, JSON.stringify({ ...payload, revision }));
        if (!submission) return;
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api(`/support/admin/cases/${encodeURIComponent(caseId)}/update`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, expected_revision: revision, confirm: true, idempotency_key: submission.key })
          });
          acknowledged = true;
          await hydrateSupportAdminCase(caseId);
          toast(result.message || "Đã cập nhật triage Support Desk.");
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
      if (action === "memory-note-filter" || action === "memory-note-filter-clear") {
        const filter = action === "memory-note-filter-clear"
          ? { q: "", priority: "", state: "all" }
          : memoryNoteFilterPayload(fields);
        await hydrateMemoryCenter(filter);
        toast(filter.q || filter.priority || filter.state !== "all" ? "Đã áp dụng bộ lọc ghi chú." : "Đã hiển thị toàn bộ ghi chú Web.");
        return;
      }
      if (action === "memory-refresh") {
        await hydrateMemoryCenter();
        toast("Đã làm mới Memory Center từ Web account hiện tại.");
        return;
      }
      if (action === "memory-note-open") {
        const noteId = String(detail.memoryNoteId || "").trim();
        if (!validMemoryId(noteId)) throw new Error("Mã ghi chú Memory Center không hợp lệ.");
        await hydrateMemoryNote(noteId);
        return;
      }
      if (action === "memory-note-create") {
        const payload = memoryNotePayload(fields);
        const scope = "memory:note:create";
        const submission = acquireSubmission(scope, JSON.stringify(payload));
        if (!submission) {
          toast("Ghi chú đang được lưu. Vui lòng chờ phản hồi từ máy chủ.", "error");
          return;
        }
        setActionBusy(action, route, true);
        try {
          const result = await api("/memory/notes", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, idempotency_key: submission.key })
          });
          const note = result.data && result.data.note && typeof result.data.note === "object" ? result.data.note : null;
          if (!note || !validMemoryId(note.id)) throw new Error("Máy chủ chưa trả ghi chú Memory Center hợp lệ.");
          await hydrateMemoryCenter();
          await hydrateMemoryNote(note.id);
          toast(result.message || "Đã lưu ghi chú trong Memory Center.");
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "memory-note-update") {
        const noteId = String(detail.memoryNoteId || "").trim();
        const expectedRevision = validMemoryRevision(detail.memoryNoteRevision);
        if (!validMemoryId(noteId) || !expectedRevision) throw new Error("Phiên bản ghi chú không hợp lệ.");
        const payload = { ...memoryNotePayload(fields), expected_revision: expectedRevision };
        const scope = `memory:note:${noteId}:update`;
        const submission = acquireSubmission(scope, JSON.stringify(payload));
        if (!submission) return;
        setActionBusy(action, route, true);
        try {
          const result = await api(`/memory/notes/${encodeURIComponent(noteId)}/update`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, idempotency_key: submission.key })
          });
          await hydrateMemoryCenter();
          await hydrateMemoryNote(noteId);
          toast(result.message || "Đã lưu phiên bản ghi chú mới.");
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (["memory-note-archive", "memory-note-restore", "memory-note-restore-version"].includes(action)) {
        const noteId = String(detail.memoryNoteId || "").trim();
        const expectedRevision = validMemoryRevision(detail.memoryNoteRevision);
        if (!validMemoryId(noteId) || !expectedRevision) throw new Error("Phiên bản ghi chú không hợp lệ.");
        const operation = action === "memory-note-archive" ? "archive" : action === "memory-note-restore" ? "restore" : "restore-version";
        const version = action === "memory-note-restore-version" ? validMemoryRevision(detail.memoryNoteVersion) : 0;
        if (action === "memory-note-restore-version" && !version) throw new Error("Phiên bản cần khôi phục không hợp lệ.");
        const payload = { expected_revision: expectedRevision };
        const scope = `memory:note:${noteId}:${operation}${version ? `:${version}` : ""}`;
        const submission = acquireSubmission(scope, JSON.stringify({ ...payload, version }));
        if (!submission) return;
        setActionBusy(action, route, true);
        try {
          const target = operation === "restore-version"
            ? `/memory/notes/${encodeURIComponent(noteId)}/restore-version/${encodeURIComponent(String(version))}`
            : `/memory/notes/${encodeURIComponent(noteId)}/${operation}`;
          const result = await api(target, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, idempotency_key: submission.key })
          });
          await hydrateMemoryCenter();
          await hydrateMemoryNote(noteId);
          toast(result.message || "Đã cập nhật ghi chú Memory Center.");
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "memory-reminder-create") {
        const payload = memoryReminderPayload(fields);
        const scope = "memory:reminder:create";
        const submission = acquireSubmission(scope, JSON.stringify(payload));
        if (!submission) {
          toast("Reminder đang được tạo. Vui lòng chờ phản hồi từ máy chủ.", "error");
          return;
        }
        setActionBusy(action, route, true);
        try {
          const result = await api("/memory/reminders", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, idempotency_key: submission.key })
          });
          const reminder = result.data && result.data.reminder && typeof result.data.reminder === "object" ? result.data.reminder : null;
          if (!reminder || !validMemoryId(reminder.id)) throw new Error("Máy chủ chưa trả reminder hợp lệ.");
          await hydrateMemoryCenter();
          toast(result.message || "Đã tạo reminder trong Web Memory Center.");
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (action === "memory-reminder-update") {
        const reminderId = String(detail.memoryReminderId || "").trim();
        const expectedRevision = validMemoryRevision(detail.memoryReminderRevision);
        if (!validMemoryId(reminderId) || !expectedRevision) throw new Error("Phiên bản reminder không hợp lệ.");
        const payload = { ...memoryReminderPayload(fields), expected_revision: expectedRevision };
        const scope = `memory:reminder:${reminderId}:update`;
        const submission = acquireSubmission(scope, JSON.stringify(payload));
        if (!submission) return;
        setActionBusy(action, route, true);
        try {
          const result = await api(`/memory/reminders/${encodeURIComponent(reminderId)}/update`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, idempotency_key: submission.key })
          });
          await hydrateMemoryCenter();
          toast(result.message || "Đã cập nhật reminder.");
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
      if (["memory-reminder-complete", "memory-reminder-pause", "memory-reminder-resume", "memory-reminder-cancel"].includes(action)) {
        const reminderId = String(detail.memoryReminderId || "").trim();
        const expectedRevision = validMemoryRevision(detail.memoryReminderRevision);
        if (!validMemoryId(reminderId) || !expectedRevision) throw new Error("Phiên bản reminder không hợp lệ.");
        const operation = action.replace("memory-reminder-", "");
        const payload = { expected_revision: expectedRevision };
        const scope = `memory:reminder:${reminderId}:${operation}`;
        const submission = acquireSubmission(scope, JSON.stringify(payload));
        if (!submission) return;
        setActionBusy(action, route, true);
        try {
          const result = await api(`/memory/reminders/${encodeURIComponent(reminderId)}/${encodeURIComponent(operation)}`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, idempotency_key: submission.key })
          });
          await hydrateMemoryCenter();
          toast(result.message || "Đã cập nhật trạng thái reminder.");
        } finally {
          releaseSubmission(submission);
          setActionBusy(action, route, false);
        }
        return;
      }
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
      if (action === "document-operation-pdf-to-images") {
        const sourceAssetId = String(fields.source_asset_id || "").trim();
        if (!validVaultAssetId(sourceAssetId)) throw new Error("Hãy chọn một PDF riêng tư hợp lệ từ Asset Vault.");
        const scope = `document-operation:pdf-to-images:${sourceAssetId}`;
        const submission = acquireSubmission(scope, sourceAssetId);
        if (!submission) {
          toast("PDF → ảnh đang được máy chủ xử lý. Vui lòng chờ phản hồi.", "error");
          return;
        }
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api("/document-operations/pdf-to-images", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source_asset_id: sourceAssetId, idempotency_key: submission.key })
          });
          acknowledged = true;
          const operation = result.data && result.data.operation && typeof result.data.operation === "object" ? result.data.operation : null;
          if (!operation || !validDocumentOperationId(operation.id) || String(operation.kind || "") !== "pdf_to_images") {
            throw new Error("Máy chủ chưa trả metadata PDF → ảnh hợp lệ.");
          }
          await Promise.all([hydrateDocumentOperations(), hydrateAssetVault()]);
          toast(result.message || "Đã render và xác minh PNG riêng tư từ PDF.");
        } catch (error) {
          // Preserve only the server-recorded lifecycle when parsing, render,
          // pixel or ZIP verification rejects the source. There is never a
          // browser-produced fallback image or synthetic download.
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
      if (action === "image-operation-enhance") {
        const sourceAssetId = String(fields.source_asset_id || "").trim();
        const preset = String(fields.preset || "photo_clear_detail").trim();
        const basicUpscaleText = String(fields.basic_upscale || "false").trim();
        if (!validVaultAssetId(sourceAssetId)) throw new Error("Hãy chọn một ảnh private hợp lệ từ Asset Vault.");
        if (!["photo_clear_detail", "product_clean", "cinematic_warm", "fresh_blue", "food_vivid", "custom"].includes(preset)) {
          throw new Error("Công thức Image Enhance chưa hợp lệ.");
        }
        if (!["true", "false"].includes(basicUpscaleText)) throw new Error("Tùy chọn nâng kích thước cơ bản chưa hợp lệ.");
        const basicUpscale = basicUpscaleText === "true";
        const body = {
          source_asset_id: sourceAssetId,
          preset,
          basic_upscale: basicUpscale
        };
        let settingsScope = "preset";
        if (preset === "custom") {
          const parseFactor = (value, label) => {
            const text = String(value || "").trim();
            if (!/^(?:0\.[5-9]\d?|1(?:\.\d{1,2})?|2(?:\.0{1,2})?)$/.test(text)) {
              throw new Error(`${label} phải là số từ 0,50 đến 2,00.`);
            }
            const number = Number(text);
            if (!Number.isFinite(number) || number < 0.5 || number > 2) throw new Error(`${label} phải là số từ 0,50 đến 2,00.`);
            return Number(number.toFixed(2));
          };
          const tone = String(fields.tone || "neutral").trim();
          if (!["neutral", "warm", "cool", "clean"].includes(tone)) throw new Error("Tone tùy chỉnh chưa hợp lệ.");
          body.brightness = parseFactor(fields.brightness, "Độ sáng");
          body.contrast = parseFactor(fields.contrast, "Tương phản");
          body.saturation = parseFactor(fields.saturation, "Bão hòa màu");
          body.sharpness = parseFactor(fields.sharpness, "Độ nét");
          body.tone = tone;
          settingsScope = `${body.brightness}:${body.contrast}:${body.saturation}:${body.sharpness}:${tone}`;
        }
        const scope = `image-operation:enhance:${sourceAssetId}:${preset}:${settingsScope}:${basicUpscale ? "2x" : "1x"}`;
        const submission = acquireSubmission(scope, scope);
        if (!submission) {
          toast("Image Enhance Studio đang được máy chủ xử lý. Vui lòng chờ phản hồi.", "error");
          return;
        }
        let acknowledged = false;
        setActionBusy(action, route, true);
        try {
          const result = await api("/image-operations/enhance", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...body, idempotency_key: submission.key })
          });
          acknowledged = true;
          const operation = result.data && result.data.operation && typeof result.data.operation === "object" ? result.data.operation : null;
          if (!operation || !validImageOperationId(operation.id) || String(operation.kind || "") !== "image_enhance") {
            throw new Error("Máy chủ chưa trả metadata Image Enhance Studio hợp lệ.");
          }
          await Promise.all([hydrateImageEnhanceOperations(), hydrateAssetVault()]);
          toast(result.message || "Đã tạo và xác minh PNG private đã chỉnh.");
        } catch (error) {
          // A malformed/animated/tampered source must remain an honest
          // server-recorded result. No browser processing or fallback output.
          acknowledged = acknowledged || Boolean(error && Number.isInteger(error.status) && error.status > 0);
          if (acknowledged) await Promise.all([hydrateImageEnhanceOperations(), hydrateAssetVault()]);
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
      if (action === "image-enhance-refresh") {
        await Promise.all([hydrateImageEnhanceOperations(), hydrateAssetVault()]);
        toast("Đã làm mới Image Enhance Studio.");
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
      if (route === "/image/edit" && ["feature-draft", "feature-estimate", "feature-confirm"].includes(action)) {
        throw new Error("Image Enhance Studio chỉ dùng thao tác private native; không tạo draft, quote hay Job bridge.");
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
