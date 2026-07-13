"""Static contracts for the presentation-only customer portal.

These checks deliberately verify the browser bundle rather than a bot fixture:
the Web App must not turn a reported engine output into a downloadable asset
until the canonical bridge publishes a signed delivery contract.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PORTAL_CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")


def test_portal_never_offers_download_for_reported_output_metadata() -> None:
    assert "Chờ delivery canonical" in PORTAL
    assert "Có metadata output · chưa đủ delivery" in PORTAL
    assert "Metadata output đã bị giữ" in PORTAL
    assert "function assetDeliveryState(item, surface)" in PORTAL
    assert "Output hợp lệ · chờ URL ký" in PORTAL
    assert "function assetDownloadPath(item)" in PORTAL
    assert 'surface === "asset" && item.delivery_ready === true' in PORTAL
    assert '`/api/v1/assets/${encodeURIComponent(assetId)}/download`' in PORTAL
    assert "Tải tệp đã xác thực" in PORTAL
    assert "data-portal-action=\"asset-download\"" not in PORTAL
    assert "window.location.assign(`/assets/" not in PORTAL
    assert "asset-download" not in INTEGRATION
    assert "/api/operator/" not in INTEGRATION


def test_job_polling_uses_only_the_signed_web_api() -> None:
    assert "const JOB_POLL_INTERVAL_MS = 15000;" in INTEGRATION
    assert "const JOB_POLL_MAX_BACKOFF_MS = 60000;" in INTEGRATION
    assert "function scheduleJobPolling" in INTEGRATION
    assert "jobPollFailures += 1;" in INTEGRATION
    assert "retryDelay" in INTEGRATION
    assert 'api("/jobs")' in INTEGRATION
    assert "function jobIdFromPath(path)" in INTEGRATION
    assert "decodeURIComponent(raw.slice(\"/jobs/\".length))" in INTEGRATION
    assert "function exactJobRecord(value, expectedId)" in INTEGRATION
    assert "function ownedAssetsForJob(job, items)" in INTEGRATION
    assert 'api("/assets").catch(() => ({ data: { items: [] } }))' in INTEGRATION
    assert "provider" not in INTEGRATION[INTEGRATION.index("function scheduleJobPolling"):INTEGRATION.index("function featurePageStates")]


def test_job_detail_matches_only_owner_scoped_asset_metadata_before_delivery() -> None:
    assert "function exactJobAssets(job, source)" in PORTAL
    assert "function assetJobLink(item)" in PORTAL
    assert 'href="/jobs/${encodeURIComponent(assetId)}"' in PORTAL
    assert "data-job-output-assets" in PORTAL
    assert "Tài sản của job" in PORTAL
    assert 'assetDeliveryState(item, "asset")' in PORTAL
    assert "deliveryAsset || job" in PORTAL
    output_panel = PORTAL[PORTAL.index("function renderJobOutputAssets"):PORTAL.index("function canonicalXu")]
    assert "provider" not in output_panel
    assert "download_url" not in output_panel


def test_completed_output_without_delivery_offers_only_safe_ticket_recovery() -> None:
    assert "function jobNeedsDeliverySupport(job, source)" in PORTAL
    delivery = PORTAL[PORTAL.index("function jobNeedsDeliverySupport(job, source)"):PORTAL.index("function renderJobs(page, context)")]
    assert 'jobStatus(job) !== "completed"' in delivery
    assert "outputReported" in delivery
    assert "deliveryReady" in delivery
    assert "data-delivery-pending" in delivery
    assert "Ticket chỉ báo thiếu delivery" in delivery
    assert "Web không tạo URL, retry, refund hay thay đổi Xu" in delivery
    assert "download_url" not in delivery
    assert "provider" not in delivery.lower()
    contract = (ROOT / "docs" / "migration" / "JOB_SUPPORT_RECOVERY.md").read_text(encoding="utf-8")
    assert "delivery-pending" in contract
    assert "does not mint a URL" in contract


def test_problem_job_detail_can_create_only_a_safe_text_support_ticket() -> None:
    assert "function jobNeedsDeliverySupport(job, source)" in PORTAL
    assert "function renderJobRecoverySupport(job, context, source)" in PORTAL
    recovery = PORTAL[PORTAL.index("function renderJobRecoverySupport(job, context, source)"):PORTAL.index("function renderJobs(page, context)")]
    assert 'new Set(["failed", "failed_no_charge", "cancelled", "guarded"])' in recovery
    assert "Output đã xong nhưng delivery đang chờ" in recovery
    assert "Ticket chỉ báo thiếu delivery" in recovery
    assert "data-job-recovery-support" in recovery
    assert 'data-portal-action="create-ticket"' in recovery
    assert 'name="subject"' in recovery
    assert 'name="detail"' in recovery
    assert "readonly" in recovery
    assert "Mã job nằm trong chủ đề để đối chiếu thủ công" in recovery
    assert "không retry, refund hay thay đổi Xu" in recovery
    assert 'name="job_id"' not in recovery
    assert "related_job_id" not in recovery
    assert "download_url" not in recovery
    assert "/api/v1/" not in recovery
    assert "payos" not in recovery.lower()
    assert "provider" not in recovery.lower()
    job_detail = PORTAL[PORTAL.index("function renderJobDetail(page, context)"):PORTAL.index("function renderAssets(page, context)")]
    assert "${renderJobRecoverySupport(job, context, context.jobAssets)}" in job_detail


def test_dashboard_hydrates_only_canonical_metadata() -> None:
    assert 'path === "/dashboard"' in INTEGRATION
    assert 'api("/wallet")' in INTEGRATION
    assert 'api("/support/tickets").catch(() => ({ data: { items: [] } }))' in INTEGRATION
    assert "Tài sản gần đây" in PORTAL
    assert "Không đồng nghĩa delivery" in PORTAL


def test_dashboard_work_queue_uses_only_owner_scoped_canonical_metadata() -> None:
    work_queue = PORTAL[
        PORTAL.index("function renderWorkspaceActionCenter(context)"):
        PORTAL.index("function renderStudioLaunchpad(context)")
    ]
    assert "data-workspace-action-center" in work_queue
    assert "Công việc cần chú ý" in work_queue
    assert 'Array.isArray(context.jobs)' in work_queue
    assert 'Array.isArray(context.assets)' in work_queue
    assert 'Array.isArray(context.tickets)' in work_queue
    assert 'item.download_ready === true && item.delivery_ready === true' in work_queue
    assert 'canonicalTicketStatus(item) === "waiting_user"' in work_queue
    assert 'href: "/jobs"' in work_queue
    assert 'href: "/assets"' in work_queue
    assert 'href: "/tickets"' in work_queue
    assert "fetch(" not in work_queue
    assert "api(" not in work_queue
    assert "toanaas:portal-action" not in work_queue
    assert ".portal-action-center-grid" in PORTAL_CSS


def test_portal_uses_canonical_price_tiers_topup_catalog_and_real_telegram_link_flow() -> None:
    assert 'optionsFrom: "imageTiers"' in PORTAL
    assert 'optionsFrom: "videoTiers"' in PORTAL
    assert 'optionsFrom: "topupPackages"' in PORTAL
    assert 'optionsFrom: "packages"' not in PORTAL
    assert '"start-telegram-link"' in PORTAL
    assert '"start-telegram-link"' in INTEGRATION
    assert 'api("/pricing")' in INTEGRATION
    assert 'api("/packages")' in INTEGRATION
    assert 'api("/auth/telegram/link/status")' in INTEGRATION


def test_feature_flow_keeps_sanitized_form_values_and_staged_upload_ids() -> None:
    assert "const priorInput = priorFlow" in INTEGRATION
    assert "const values = { ...priorInput, ...fields };" in INTEGRATION
    assert "input: featureInput" in INTEGRATION
    assert "const fieldValues = { ...(flow && flow.input" in PORTAL
    assert "transientFormDrafts" in PORTAL
    assert "tệp đã vào staging canonical" in PORTAL


def test_quote_capable_workflows_can_estimate_directly_and_confirm_only_a_fresh_quote() -> None:
    assert 'featurePage("/chat"' in PORTAL
    assert 'action: "feature-estimate"' in PORTAL
    assert 'featurePage("/voice/tts"' in PORTAL
    assert "function flowHasFreshEstimate(flow)" in PORTAL
    assert "flow.estimateFingerprint" in PORTAL
    assert "flow.webQuoteReceipt" in PORTAL
    assert "const estimateAvailable = featurePhase === \"estimate\"" in INTEGRATION
    assert "function validWebQuoteReceipt(value)" in INTEGRATION
    assert "web_quote_receipt: priorReceipt" in INTEGRATION
    assert "webQuoteReceipt" in INTEGRATION
    assert "Thông tin đã thay đổi hoặc chưa có estimate canonical hợp lệ" in INTEGRATION
    api = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    assert "def _issue_feature_quote_receipt" in api
    assert "def _claim_feature_quote_receipt" in api
    assert "FEATURE_ESTIMATE_REQUIRED" in api
    database = (ROOT / "copyfast_db.py").read_text(encoding="utf-8")
    assert "web_feature_quote_receipts" in database
    assert "token_hash TEXT PRIMARY KEY" in database


def test_feature_submissions_are_single_flight_and_reuse_an_idempotency_key_for_a_matching_input() -> None:
    assert "const draftScope = `feature:${route}:${featurePhase}`;" in INTEGRATION
    assert "featureSubmission = acquireSubmission(draftScope, initialFingerprint);" in INTEGRATION
    assert "idempotency_key: featureSubmission.key" in INTEGRATION
    assert "setActionBusy(action, route, true);" in INTEGRATION
    assert "setActionBusy(action, route, false);" in INTEGRATION


def test_workflow_forms_follow_the_supported_bot_contracts_before_staging() -> None:
    assert "videoStoryboard" in PORTAL
    assert 'name: "duration_seconds"' in PORTAL
    assert 'name: "platform"' in PORTAL
    assert 'name: "template"' in PORTAL
    assert 'name: "voice_profile_id"' in PORTAL
    assert "requiredUpload: true" in PORTAL
    assert '"image_to_pdf"' in PORTAL
    assert "LANGUAGE_OPTIONS" in PORTAL
    assert "function validateFeatureIntake(feature, route, fields, phase)" in INTEGRATION
    assert "Voice Clone cần một mẫu audio" in INTEGRATION
    assert "Gộp PDF cần ít nhất hai tệp" in INTEGRATION
    assert "Image-to-Video chỉ nhận JPG, PNG hoặc WebP" in INTEGRATION


def test_storyboard_and_image_to_image_keep_their_bot_specific_intake_contracts() -> None:
    assert "contentStoryboard" in PORTAL
    assert 'name: "template"' in PORTAL
    assert 'name: "duration", label: "Thời lượng mục tiêu (giây)"' in PORTAL
    assert 'featurePage("/content/storyboard"' in PORTAL
    assert "FIELD_SETS.contentStoryboard" in PORTAL
    assert "imageTransform" in PORTAL
    assert 'featurePage("/image/transform"' in PORTAL
    assert "FIELD_SETS.imageTransform" in PORTAL
    assert '"image_transform", "image_remove_background"' in INTEGRATION


def test_video_music_and_dubbing_forms_forward_the_bot_planning_controls() -> None:
    image_to_video = PORTAL[PORTAL.index("videoImageToVideo:"):PORTAL.index("voice: [")]
    assert 'name: "platform"' in image_to_video
    assert 'name: "goal"' in image_to_video
    music_song = PORTAL[PORTAL.index("musicSong:"):PORTAL.index("musicSfx:")]
    assert 'name: "mode"' in music_song
    assert 'name: "song_length_mode"' in music_song
    assert "Bắt buộc khi chọn Theo số giây" in music_song
    dubbing = PORTAL[PORTAL.index("dubbing: ["):PORTAL.index("documentPdf:")]
    assert 'name: "voice_profile_id"' in dubbing
    assert 'optionsFrom: "voiceProfiles"' in dubbing
    assert 'path === "/tts" || path === "/dubbing" || path.startsWith("/voice")' in INTEGRATION
    assert 'api("/voice/profiles")' in INTEGRATION
    assert "if (feature === \"music_song\")" in INTEGRATION
    assert "Khi chọn Theo số giây" in INTEGRATION


def test_read_only_subtitle_asset_scope_uses_explicit_feature_keys() -> None:
    assert "const SUBTITLE_ASSET_FEATURES" in PORTAL
    assert '"subtitle_asr", "subtitle_create", "subtitle_translate", "video_dub", "asr"' in PORTAL
    assert "function assetMatchesReadOnlyScope(item, scope)" in PORTAL
    assert "if (scope === \"subtitle\") return SUBTITLE_ASSET_FEATURES.has(feature);" in PORTAL


def test_translation_upload_and_image_create_forms_match_the_frozen_bot_contract() -> None:
    for code in ("zh_cn", "zh_tw", "th", "fr", "ar", "hi", "km", "fil", "auto"):
        assert f'value: "{code}"' in PORTAL
        assert f'"{code}"' in INTEGRATION
    assert "CANONICAL_TARGET_LANGUAGE_CODES" in INTEGRATION
    assert "const MAX_FEATURE_UPLOADS = 8;" in INTEGRATION
    assert INTEGRATION.index("if (fileCount > MAX_FEATURE_UPLOADS)") < INTEGRATION.index("async function payloadFor")
    prompt = PORTAL[PORTAL.index("prompt: ["):PORTAL.index("contentStoryboard:")]
    assert 'name: "language"' not in prompt
    assert "helper content/prompt P0 hiện trả bản nháp tiếng Việt" in prompt
    image_create = PORTAL[PORTAL.index("imageCreate:"):PORTAL.index("imageSource:")]
    assert 'name: "reference"' not in image_create
    assert "Ưu tiên tỷ lệ khi chạy" in image_create
    assert "Ưu tiên tỷ lệ bạn chọn" in PORTAL


def test_keyboard_forms_and_mobile_navigation_are_accessible() -> None:
    assert 'type="submit"' in PORTAL
    assert "form.reportValidity()" in PORTAL
    assert "dispatchAction(event.target, getBootstrap());" in PORTAL
    assert "function focusSnapshot()" in PORTAL
    assert "function restoreFocus(snapshot)" in PORTAL
    assert "sidebar.setAttribute(\"aria-modal\", \"true\")" in PORTAL
    assert "function setWorkspaceInert(opened)" in PORTAL
    assert '"/wallet/topup", "Nạp Xu"' in PORTAL
    assert '"/packages", "Gói dịch vụ"' in PORTAL
    assert '"/features", "Tất cả công cụ"' in PORTAL
    css = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in css
    assert 'data-portal-close-menu' in PORTAL
    assert "function setSidebarMenuState(button, opened)" in PORTAL
    assert 'button.setAttribute("aria-label", opened ? "Đóng điều hướng" : "Mở điều hướng")' in PORTAL
    assert "function closeSidebarAboveMobileBreakpoint()" in PORTAL
    assert 'window.addEventListener("resize", closeSidebarAboveMobileBreakpoint);' in PORTAL
    assert 'window.matchMedia("(min-width: 981px)")' in PORTAL
    assert ".portal-sidebar-close" in css
    assert ".portal-session-copy { display: none; }" in css
    assert "100dvh" in css
    assert "safe-area-inset-bottom" in css
    assert ".portal-toast-region" in css
    shell = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")
    assert "viewport-fit=cover" in shell


def test_mobile_workspace_dock_is_signed_session_only_and_navigation_only() -> None:
    shell = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")
    assert 'data-portal-mobile-nav' in shell
    assert 'aria-label="Điều hướng nhanh"' in shell
    assert "function isMobileNavCurrent(key, page)" in PORTAL
    assert "function renderMobileNav(page)" in PORTAL
    dock = PORTAL[PORTAL.index("function renderMobileNav(page)"):PORTAL.index("function renderSidebar(page, context)")]
    for label in ("Tổng quan", "AI Studio", "Jobs", "Tài sản", "Tài khoản"):
        assert label in dock
    assert "fetch(" not in dock
    assert "dispatchAction(" not in dock
    assert "const showMobileNav = !minimalShell && context.session && context.session.authenticated === true;" in PORTAL
    assert "mobileNav.hidden = !showMobileNav;" in PORTAL
    assert ".portal-mobile-nav" in PORTAL_CSS
    assert "grid-template-columns: repeat(5, minmax(0, 1fr));" in PORTAL_CSS
    assert "calc(92px + var(--portal-safe-bottom))" in PORTAL_CSS
    assert "bottom: calc(84px + var(--portal-safe-bottom));" in PORTAL_CSS


def test_command_palette_is_session_scoped_navigation_without_data_actions() -> None:
    shell = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")
    assert 'data-portal-command-palette' in shell
    assert 'id="portal-command-palette"' in shell
    assert "function commandPaletteItems(context, page)" in PORTAL
    assert "function renderCommandPalette(page, context)" in PORTAL
    palette = PORTAL[PORTAL.index("function commandPaletteItems(context, page)"):PORTAL.index("function renderSidebar(page, context)")]
    assert 'candidate.access === "public"' in palette
    assert 'candidate.access === "admin" && !(context && context.isAdmin === true)' in palette
    assert "fetch(" not in palette
    assert "dispatchAction(" not in palette
    assert 'role="dialog" aria-modal="true"' in palette
    assert 'data-portal-command-search' in palette
    assert "function openCommandPalette(trigger)" in PORTAL
    assert "function closeCommandPalette(options)" in PORTAL
    assert "function setCommandPaletteBackgroundInert(opened)" in PORTAL
    assert 'String(event.key || "").toLowerCase() === "k"' in PORTAL
    assert 'event.key === "Escape" && paletteOpen' in PORTAL
    assert ".portal-command-palette" in PORTAL_CSS
    assert ".portal-command-dialog" in PORTAL_CSS
    assert ".portal-body--command-palette" in PORTAL_CSS


def test_nav_highlights_route_families_instead_of_only_each_launch_route() -> None:
    assert "function matchesRouteFamily(path, root)" in PORTAL
    assert 'if (linkPath === "/image/create") return path === "/image" || matchesRouteFamily(path, "/image");' in PORTAL
    assert 'if (linkPath === "/video/create") return path === "/video" || matchesRouteFamily(path, "/video");' in PORTAL
    assert 'if (linkPath === "/voice/tts") return path === "/tts" || matchesRouteFamily(path, "/voice");' in PORTAL
    assert 'if (linkPath === "/subtitle") return matchesRouteFamily(path, "/subtitle") || ["/translate", "/dubbing", "/asr"].includes(path);' in PORTAL
    assert 'if (linkPath === "/admin") {' in PORTAL
    assert '["/admin", "Tất cả module", ICONS.admin]' in PORTAL
    assert '["/video/create", "Video", ICONS.video]' in PORTAL


def test_feature_catalog_discloses_all_mapped_customer_workflows_without_faking_readiness() -> None:
    assert 'customerPage("/features", "Tất cả công cụ"' in PORTAL
    assert 'layout: "feature-catalog"' in PORTAL
    assert 'case "feature-catalog": return renderFeatureCatalog(page, context);' in PORTAL
    assert "function renderFeatureCatalog(page, context)" in PORTAL
    assert "function customerCatalog(context)" in PORTAL
    assert 'entry.kind !== "admin"' in PORTAL
    assert "Object.values(manifest)" in PORTAL
    assert "function fallbackCatalogGroup(path)" in PORTAL
    assert "catalog: Array.isArray(source.catalog) ? source.catalog.slice() : []" in PORTAL
    assert "source.catalog.slice(0, 24)" not in PORTAL
    assert "Một số workspace tiêu biểu" in PORTAL
    assert 'href="/features">Xem tất cả công cụ' in PORTAL
    assert "Core Bridge chưa cấp metadata route" in PORTAL
    assert "function catalogEntryState(module, page, context)" in PORTAL
    assert "context.readiness.features[key]" in PORTAL
    assert '"/music/sfx-library": "sfx_library"' in INTEGRATION
    assert 'readOnlyPage("/music/sfx-library", "Thư viện SFX"' in PORTAL
    assert 'page.path === "/music/sfx-library" ? "sfx"' in PORTAL
    assert 'href: "/music/sfx-library", label: "Mở thư viện SFX"' in PORTAL
    assert 'class="portal-feature-jumps" aria-label="Đi tới nhóm công cụ"' in PORTAL
    assert 'href="#feature-group-${safeText(group.key)}"' in PORTAL
    assert ".portal-feature-jumps" in (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
    assert 'data-portal-catalog-search' in PORTAL
    assert "function normalizeCatalogSearch(value)" in PORTAL
    assert "function filterFeatureCatalog(value)" in PORTAL
    assert 'data-catalog-item' in PORTAL
    assert 'data-catalog-group' in PORTAL
    assert 'data-portal-catalog-clear' in PORTAL
    assert "filterFeatureCatalog(event.target.value)" in PORTAL
    assert ".portal-catalog-search" in (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")


def test_feature_family_navigators_only_link_registered_workflows_and_keep_guarded_state() -> None:
    assert 'const FEATURE_FAMILY_KEYS = Object.freeze(["content", "image", "video", "voice", "music", "subtitle", "documents"])' in PORTAL
    assert "function featureFamilyForPath(path)" in PORTAL
    assert "function registeredFeatureFamilyEntries(context, familyKey)" in PORTAL
    assert "manifest[normalizePath(route)]" in PORTAL
    assert "Never turn an inventory-only route into a clickable module card" in PORTAL
    assert "function renderFeatureFamily(page, context)" in PORTAL
    assert 'case "feature-family": return renderFeatureFamily(page, context);' in PORTAL
    assert 'const featureFamily = featureFamilyForPath(normalized);' in PORTAL
    assert 'layout: "feature-family"' in PORTAL
    assert 'href="/features/${safeText(group.key)}"' in PORTAL
    assert "Card guarded giữ nguyên trạng thái" in PORTAL
    family_renderer = PORTAL[PORTAL.index("function renderFeatureFamily(page, context)"):PORTAL.index("function normalizeCatalogSearch(value)")]
    assert "/api/v1/" not in family_renderer
    assert "payos" not in family_renderer.lower()
    pages = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
    for path, title in {
        "/features/content": "Content & Chat",
        "/features/image": "Image Studio",
        "/features/video": "Video Studio",
        "/features/voice": "Voice Studio",
        "/features/music": "Music & SFX",
        "/features/subtitle": "Phụ đề & ngôn ngữ",
        "/features/documents": "Documents & PDF",
    }.items():
        assert f'"{path}": "{title}"' in pages


def test_resolved_portal_page_title_beats_the_generic_server_placeholder_for_aliases() -> None:
    assert "function displayPageTitle(page, context)" in PORTAL
    assert 'serverTitle !== "TOAN AAS"' in PORTAL
    assert "displayPageTitle(page, context)" in PORTAL
    assert "document.title = `${displayPageTitle(page, context)} · TOAN AAS`;" in PORTAL


def test_hero_never_submits_an_empty_duplicate_feature_form_action() -> None:
    assert "const hasFields = Array.isArray(page.fields) && page.fields.length > 0;" in PORTAL
    assert "const showHeroAction = hasAction && !hasFields;" in PORTAL
    assert "duplicate hero button used to emit an empty action" in PORTAL
    assert "field values, staged upload IDs and the current quote fingerprint" in PORTAL


def test_pending_link_code_hides_duplicate_hero_action_and_requires_confirmation() -> None:
    assert "const linkPending = page.action === \"start-telegram-link\"" in PORTAL
    assert 'data-portal-confirm="Tạo mã mới sẽ hủy mã đang hiển thị.' in PORTAL
    assert "if (confirmation && !window.confirm(confirmation)) return;" in PORTAL


def test_account_uses_scoped_profile_metadata_and_server_side_logout() -> None:
    assert 'layout: "account", fields: [], action: "none", status: "ready"' in PORTAL
    assert "Hồ sơ & liên kết" in PORTAL
    assert 'data-portal-action="update-profile"' in PORTAL
    assert 'badge(profileEnabled ? "ready" : "guarded")' in PORTAL
    assert "Telegram identity, role, Xu, PayOS và provider" in PORTAL
    assert 'data-portal-action="auth-logout"' in PORTAL
    assert '"auth-logout": Boolean(account && me.csrf_token)' in INTEGRATION
    assert 'api("/auth/logout"' in INTEGRATION


def test_account_activity_is_a_sanitized_web_owned_owner_history() -> None:
    assert 'customerPage("/account/activity", "Hoạt động tài khoản"' in PORTAL
    assert 'layout: "account-activity", fields: [], action: "none", status: "read_only"' in PORTAL
    assert 'case "account-activity": return renderAccountActivity(page, context);' in PORTAL
    assert "function renderAccountActivity(page, context)" in PORTAL
    assert 'data-portal-action="refresh-account-activity"' in PORTAL
    activity = PORTAL[PORTAL.index("function accountActivityStatus"):PORTAL.index("function renderLegal")]
    assert "Nhật ký Web riêng tư" in activity
    assert "Không target/detail/request ID" in activity
    assert "canonical_user_id" not in activity
    assert "telegram_id" not in activity
    assert '"refresh-account-activity": Boolean(account)' in INTEGRATION
    assert "async function hydrateAccountActivity()" in INTEGRATION
    assert 'api("/account/activity")' in INTEGRATION
    assert 'if (account && currentPath === "/account/activity") await hydrateAccountActivity();' in INTEGRATION
    api = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    assert '@router.get("/account/activity")' in api
    assert "SELECT action, outcome, created_at" in api
    assert "WHERE account_id=?" in api
    assert "target, detail" not in api[api.index("async def account_activity"):api.index("@router.get(\"/wallet\")")]
    db = (ROOT / "copyfast_db.py").read_text(encoding="utf-8")
    assert "idx_web_audit_account_created" in db


def test_workspace_drafts_are_web_owned_and_never_resume_canonical_state() -> None:
    assert 'customerPage("/workspace", "Bản nháp của tôi"' in PORTAL
    assert 'layout: "workspace-drafts", type: "workspace-drafts", fields: [], action: "none", status: "read_only"' in PORTAL
    assert 'case "workspace-drafts": return renderWorkspaceDrafts(page, context);' in PORTAL
    assert "function renderWorkspaceDrafts(page, context)" in PORTAL
    normalizer = PORTAL[PORTAL.index("function normalizeBootstrap(raw)"):PORTAL.index("function getBootstrap()")]
    assert "workspaceDrafts: Array.isArray(source.workspaceDrafts) ? source.workspaceDrafts.slice(0, 100) : []" in normalizer
    assert "function restoreWorkspaceDraft(route, input, draftId)" in PORTAL
    assert 'data-portal-action="workspace-draft-save"' in PORTAL
    form = PORTAL[PORTAL.index("function renderFormCard(page, context)"):PORTAL.index("function renderHero")]
    assert "workspaceDraftEnabled" in form
    assert "workspaceDraftSupported" in form
    assert "context.workspaceDraftFeatures.includes(feature)" in form
    assert "workspaceDraftIdForRoute(route)" in form
    assert "workspace-draft-update" in form
    assert "Lưu thành bản mới" in form
    assert "formFieldsEnabled" in form
    assert "const localAuthoringOnly = !enabled && workspaceDraftEnabled;" in form
    assert "const formAction = localAuthoringOnly ? localDraftAction : page.action;" in form
    assert 'data-portal-action="${safeText(formAction)}"' in form
    assert "primaryActionLabel = localAuthoringOnly ? localDraftLabel" in form
    assert "Bản nháp chỉ giữ brief scalar trên Web" in form
    restore = PORTAL[PORTAL.index("function restoreWorkspaceDraft(route, input, draftId)"):PORTAL.index("function dispatchAction")]
    assert "voice_profile_id" in restore
    assert "upload_ids" in restore
    assert "field.type !== \"file\"" in restore
    assert "localStorage" not in restore
    assert "transientWorkspaceDraftIds" in restore
    assert "validWorkspaceDraftId(draftId)" in restore
    assert '"workspace-draft-update"' in PORTAL
    assert "workspaceDraftId:" in PORTAL
    assert '"workspace-draft-save": Boolean(account && me.csrf_token)' in INTEGRATION
    assert "item.web_workspace_draft_supported === true" in INTEGRATION
    assert "webWorkspaceDraftFeatures" in INTEGRATION
    assert "function workspaceDraftInput(fields)" in INTEGRATION
    assert "async function hydrateWorkspaceDrafts()" in INTEGRATION
    assert 'api("/workspace/drafts?include_archived=true")' in INTEGRATION
    assert 'api(`/workspace/drafts/${encodeURIComponent(draftId)}`)' in INTEGRATION
    assert "workspace-draft-resume" in INTEGRATION
    assert "workspace-draft-archive" in INTEGRATION
    assert 'action === "workspace-draft-save" || action === "workspace-draft-update"' in INTEGRATION
    assert 'method: updating ? "PATCH" : "POST"' in INTEGRATION
    assert "restoreWorkspaceDraft(item.route, item.input, item.id)" in INTEGRATION
    api = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    start = api.index('@router.get("/workspace/drafts")')
    end = api.index('@router.get("/core/me")')
    workspace_api = api[start:end]
    assert '@router.get("/workspace/drafts/{draft_id}")' in workspace_api
    assert '@router.post("/workspace/drafts")' in workspace_api
    assert '@router.patch("/workspace/drafts/{draft_id}")' in workspace_api
    assert '@router.post("/workspace/drafts/{draft_id}/archive")' in workspace_api
    assert "_bridge(" not in workspace_api
    assert "upload_ids" in api
    assert "voice_profile_id" in api
    assert 'item["web_workspace_draft_supported"]' in api
    db = (ROOT / "copyfast_db.py").read_text(encoding="utf-8")
    assert "web_workspace_drafts" in db
    assert "idx_web_workspace_drafts_account_state_updated" in db


def test_portal_normalizer_preserves_owner_scoped_hydration_state() -> None:
    """Successful signed reads must survive every presentation rerender."""
    normalizer = PORTAL[PORTAL.index("function normalizeBootstrap(raw)"):PORTAL.index("function getBootstrap()")]
    for expected in (
        "workspaceDrafts: Array.isArray(source.workspaceDrafts) ? source.workspaceDrafts.slice(0, 100) : []",
        "vaultItems: Array.isArray(source.vaultItems) ? source.vaultItems.slice(0, 100) : []",
        "campaignPlanDetail: source.campaignPlanDetail && typeof source.campaignPlanDetail === \"object\" ? source.campaignPlanDetail : {}",
        "accountActivity: Array.isArray(source.accountActivity) ? source.accountActivity.slice(0, 50) : []",
        "assetFilter: typeof source.assetFilter === \"string\" ? source.assetFilter : \"all\"",
        "ticketFilter: typeof source.ticketFilter === \"string\" ? source.ticketFilter : \"all\"",
        "pwaEnabled: source.pwaEnabled === true",
    ):
        assert expected in normalizer


def test_project_center_is_a_web_owned_versioned_workspace_without_bot_execution() -> None:
    projects = (ROOT / "copyfast_projects.py").read_text(encoding="utf-8")
    assert 'router = APIRouter(prefix="/api/v1/projects"' in projects
    assert 'CREATE TABLE IF NOT EXISTS web_projects' in (ROOT / "copyfast_db.py").read_text(encoding="utf-8")
    assert 'CREATE TABLE IF NOT EXISTS web_studio_documents' in (ROOT / "copyfast_db.py").read_text(encoding="utf-8")
    assert 'CREATE TABLE IF NOT EXISTS web_studio_document_versions' in (ROOT / "copyfast_db.py").read_text(encoding="utf-8")
    assert "STUDIO_DOCUMENT_CONFLICT" in projects
    assert "web.studio_document.restore" in projects
    assert "from copyfast_bridge" not in projects
    assert "bridge_request" not in projects
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "import copyfast_projects" in app
    assert "app.include_router(copyfast_projects.router)" in app
    registry = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")
    assert 'WebFeature("projects", "Project Center"' in registry
    pages = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
    assert "PROJECT_PATH" in pages
    assert 'customerPage("/projects", "Project Center"' in PORTAL
    assert 'layout: "project-center"' in PORTAL
    assert 'layout: "project-detail"' in PORTAL
    assert "function renderProjectCenter(page, context)" in PORTAL
    assert "function renderProjectDetail(page, context)" in PORTAL
    assert 'case "project-center": return renderProjectCenter(page, context);' in PORTAL
    assert 'case "project-detail": return renderProjectDetail(page, context);' in PORTAL
    assert '"project-create": Boolean(account && me.csrf_token)' in INTEGRATION
    assert "async function hydrateProjects()" in INTEGRATION
    assert "async function hydrateProjectDetail(path)" in INTEGRATION
    assert "async function hydrateStudioDocument(documentId)" in INTEGRATION
    assert 'api("/projects")' in INTEGRATION
    assert 'api(`/projects/${encodeURIComponent(projectId)}`)' in INTEGRATION


def test_asset_vault_is_a_separate_private_web_surface() -> None:
    assets = (ROOT / "copyfast_assets.py").read_text(encoding="utf-8")
    database = (ROOT / "copyfast_db.py").read_text(encoding="utf-8")
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    registry = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")
    assert 'router = APIRouter(prefix="/api/v1/asset-vault"' in assets
    assert "web_asset_files" in database
    assert "asset_vault_directory" in database
    assert "copyfast_bridge" not in assets
    assert "bridge_request" not in assets
    assert "app.include_router(copyfast_assets.router)" in app
    assert 'WebFeature("asset_vault", "Asset Vault"' in registry
    assert 'customerPage("/asset-vault", "Asset Vault"' in PORTAL
    assert 'layout: "asset-vault"' in PORTAL
    assert "function renderAssetVault(page, context)" in PORTAL
    assert 'case "asset-vault": return renderAssetVault(page, context);' in PORTAL
    vault_renderer = PORTAL[PORTAL.index("function renderAssetVault(page, context)"):PORTAL.index("function renderTickets(page, context)")]
    assert 'data-portal-action="asset-vault-upload"' in vault_renderer
    assert 'data-portal-action="asset-vault-archive"' in vault_renderer
    assert "/api/v1/assets/" not in vault_renderer
    assert 'api("/asset-vault")' in INTEGRATION
    assert "async function hydrateAssetVault()" in INTEGRATION
    assert '"asset-vault-upload": Boolean(account && me.csrf_token && assetVaultEnabled)' in INTEGRATION
    assert "FormData()" in INTEGRATION
    assert "/api/v1/asset-vault" in SERVICE_WORKER
    assert ".portal-vault-dropzone" in PORTAL_CSS


def test_registration_explains_real_login_methods_and_profile_defaults() -> None:
    assert "Hồ sơ mặc định sau khi tạo" in PORTAL
    assert "Locale Tiếng Việt · múi giờ Asia/Ho_Chi_Minh · avatar gradient" in PORTAL
    assert "Không nhập ID Telegram thô" in PORTAL
    assert "Email + mật khẩu (có thể dùng Gmail) đang hoạt động" in PORTAL
    assert "Telegram Login, Google OAuth, GitHub OAuth và Sign in with Apple chỉ mở khi server có cấu hình thật" in PORTAL
    assert "function renderOAuthRegistrationMethods(context)" in PORTAL
    assert "Tạo hoặc tiếp tục với OAuth" in PORTAL
    assert 'renderPublicOAuthCard("telegram", "Telegram Login", telegramOidcEnabled, "✈", "register")' in PORTAL
    assert 'renderPublicOAuthCard("google", "Google (OAuth)", googleEnabled, "G", "register")' in PORTAL
    assert 'renderPublicOAuthCard("github", "GitHub", githubEnabled, "◎", "register")' in PORTAL
    assert 'renderPublicOAuthCard("apple", "Sign in with Apple", appleEnabled, "", "register")' in PORTAL
    assert "portal-auth-notes" in PORTAL
    assert "Browser không nhận hoặc lưu Telegram ID" in PORTAL
    css = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
    assert ".portal-auth-notes" in css
    assert "overflow-wrap: anywhere" in css


def test_initial_hydration_is_deduplicated_and_bfcache_refresh_is_explicit() -> None:
    assert "function startInitialHydration()" in INTEGRATION
    assert "if (!initialHydration) initialHydration = hydrate().catch(() => {});" in INTEGRATION
    assert 'window.addEventListener("pageshow", (event) => {' in INTEGRATION
    assert "if (event.persisted) {" in INTEGRATION
    assert "hydrate().then(() => {" in INTEGRATION


def test_login_return_path_is_internal_and_web_workspace_is_independent() -> None:
    assert "function safeReturnPath(value)" in INTEGRATION
    assert 'route.startsWith("//")' in INTEGRATION
    assert 'route.includes("?") || route.includes("#")' in INTEGRATION
    assert 'window.location.assign(requested || "/dashboard");' in INTEGRATION
    assert "account.canonical_user_id" not in INTEGRATION


def test_payment_ui_only_renders_vetted_canonical_checkout_data() -> None:
    assert "function safePayosCheckout(value)" in PORTAL
    assert 'url.hostname === "pay.payos.vn"' in PORTAL
    assert "!url.username && !url.password && !url.port && !url.hash" in PORTAL
    assert "Yêu cầu thanh toán canonical" in PORTAL
    assert 'data-portal-action="refresh-payment"' in PORTAL
    assert 'api(`/payments/${encodeURIComponent(paymentId)}`)' in INTEGRATION
    assert "paymentFlow" in INTEGRATION
    assert "const PAYMENT_STATUS_LABELS" in PORTAL
    assert 'queued: "Chờ thanh toán"' in PORTAL


def test_payment_entry_ux_keeps_manual_topup_inside_the_linked_bot_and_polls_only_the_web_api() -> None:
    assert "function renderPaymentEntryPoints(context)" in PORTAL
    assert 'manual.command === "/thucong"' in PORTAL
    assert 'payos.command === "/naptien"' in PORTAL
    assert 'data-portal-action="copy-payment-command"' in PORTAL
    assert "function renderPaymentRequestForm(page, context)" in PORTAL
    assert "Không dùng catalog combo/gói tháng để giả làm mệnh giá nạp Xu." in PORTAL
    assert "function paymentWebCatalogReady(context)" in PORTAL
    assert "payos.topup_catalog_available === true" in PORTAL
    assert "Web không suy đoán QR luôn sẵn sàng." in PORTAL
    api = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    assert "def _payment_topup_packages()" in api
    assert '"topup_packages": topup_packages' in api
    assert "PAYMENT_PACKAGE_NOT_IN_CATALOG" in api
    assert 'optionsFrom: "topupPackages"' in PORTAL
    assert 'field.optionsFrom === "topupPackages"' in PORTAL
    assert "Không nhập ảnh bill, số tài khoản, OTP, TXID hay thông tin thẻ vào Web App." in PORTAL
    assert "function renderPaymentLookup(context)" in PORTAL
    assert 'data-portal-action="payment-lookup"' in PORTAL
    assert "const PAYMENT_POLL_INTERVAL_MS = 10000;" in INTEGRATION
    assert "function schedulePaymentPolling" in INTEGRATION
    assert "function copyPaymentBotCommand(value)" in INTEGRATION
    assert '["/naptien", "/thucong"].includes(command)' in INTEGRATION
    assert 'data-portal-action="refresh-wallet-after-bot"' in PORTAL
    assert '"refresh-wallet-after-bot": Boolean(bridgeAvailable)' in INTEGRATION
    assert 'if (action === "refresh-wallet-after-bot")' in INTEGRATION
    assert "Chỉ đơn PayOS canonical" in PORTAL
    assert "Nạp thủ công không xuất hiện ở Web" in PORTAL
    assert "TICKET_MANUAL_PAYMENT_PROOF_PATTERN" in (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    assert "SUPPORT_MANUAL_PAYMENT_PROOF_PATTERN" in INTEGRATION
    assert 'api("/payments/options")' in INTEGRATION
    assert 'if (account && telegramLinked && currentPath === "/wallet/topup") await hydratePaymentOptions();' in INTEGRATION
    assert "/api/v1/billing/create-payment-link" not in PORTAL
    assert "/api/v1/billing/create-payment-link" not in INTEGRATION


def test_manual_topup_guide_is_an_honest_bot_handoff_not_a_second_receipt_system() -> None:
    assert "function renderManualTopupGuide(context)" in PORTAL
    assert "Nạp thủ công: tiếp tục trong Telegram" in PORTAL
    assert "Nạp VND: gửi ảnh bill trong Bot." in PORTAL
    assert "Nạp quốc tế/USDT: gửi TXID đầy đủ hoặc ảnh bill trong Bot." in PORTAL
    assert "const routeGuide =" in PORTAL
    assert "Không có QR tĩnh" in PORTAL
    assert "Không dán TXID vào Web" in PORTAL
    assert "const stateGuide =" in PORTAL
    assert "pending</code> hoặc <code>pending_admin_review" in PORTAL
    assert "pending_admin_review" in PORTAL
    assert "approved" in PORTAL
    assert "rejected" in PORTAL
    assert "wallet_history_signal_available" in PORTAL
    assert "history_in_web === false" in PORTAL
    assert "Lịch sử nạp thủ công" in PORTAL
    assert 'Sao chép ${safeText(historyCommand)}' in PORTAL
    assert '>Mở Bot</a>' in PORTAL
    assert "Mở Bot để xem lịch sử" not in PORTAL
    assert "const manualActions = manualAvailable" in PORTAL
    assert "Chưa có URL Bot hợp lệ để bắt đầu nạp thủ công." in PORTAL
    assert "Kiểm tra đơn PayOS" in PORTAL
    assert "mã được bot tạo cho luồng thủ công" not in PORTAL
    assert "pending_deposits" not in PORTAL
    assert "pending_deposits" not in INTEGRATION
    assert "manual-topup" not in INTEGRATION
    guide = PORTAL[PORTAL.index("function renderManualTopupGuide(context)"):PORTAL.index("function renderPaymentRequestForm(page, context)")]
    assert "<input" not in guide
    assert "<textarea" not in guide
    assert "data-portal-action=\"payment-create\"" not in guide
    assert ".portal-manual-topup-routes" in PORTAL_CSS
    assert ".portal-manual-topup-status" in PORTAL_CSS


def test_job_and_payment_statuses_are_not_conflated() -> None:
    assert "function paymentStatus(item)" in PORTAL
    assert 'paid: "completed"' in PORTAL
    job_slice = PORTAL[PORTAL.index("function jobStatus(item)"):PORTAL.index("function paymentStatus(item)")]
    assert 'paid: "completed"' not in job_slice
    assert '"cancelled", "Đã hủy"' in PORTAL
    assert '"refunded", "Đã hoàn Xu"' in PORTAL


def test_readiness_maps_all_feature_route_aliases_not_only_catalog_routes() -> None:
    assert "Object.entries(FEATURE_BY_PATH).forEach" in INTEGRATION
    assert 'api("/features/status")' in INTEGRATION
    assert "function safeFeatureExecutionFeatures(value)" in INTEGRATION
    assert "featurePageStates(base().catalog || [], readiness.data || {}, base().bridge && base().bridge.featureExecutionFeatures)" in INTEGRATION
    assert 'path === "/tts" || path === "/dubbing" || path.startsWith("/voice")' in INTEGRATION
    assert 'context.pageStates[normalizePath(context.path)]' in PORTAL


def test_client_capabilities_respect_the_copyfast_master_flag() -> None:
    assert "const copyfastEnabled = Boolean(status.flags && status.flags.copyfast_enabled);" in INTEGRATION
    assert "const bridgeAvailable = Boolean(copyfastEnabled" in INTEGRATION
    assert '"refresh-admin": Boolean(status.flags && status.flags.admin_erp_enabled' in INTEGRATION


def test_pwa_caches_only_the_fixed_public_shell() -> None:
    assert 'const SHELL = Object.freeze([' in SERVICE_WORKER
    assert 'const SHELL_PATHS = new Set(SHELL);' in SERVICE_WORKER
    assert '!SHELL_PATHS.has(url.pathname)' in SERVICE_WORKER
    assert 'cache.put(' not in SERVICE_WORKER
    assert '"/api/' not in SERVICE_WORKER
    assert 'wallet, payment, admin' in SERVICE_WORKER
    assert 'fetch(request).catch(() => caches.match(url.pathname).then((cached) => cached || Response.error()))' in SERVICE_WORKER
    # A public-shell change must invalidate the prior PWA shell bundle.
    assert 'portal-shell-v6' in SERVICE_WORKER


def test_public_landing_hides_authenticated_shell_without_leaving_a_layout_slot() -> None:
    assert "const minimalShell = isLanding || isAuth" in PORTAL
    assert "sidebar.hidden = minimalShell" in PORTAL
    assert "header.hidden = minimalShell" in PORTAL
    assert 'shell.classList.toggle("portal-shell--auth", isAuth)' in PORTAL
    assert 'document.body.classList.toggle("portal-body--auth", isAuth)' in PORTAL
    assert "portal-auth-brand" in PORTAL
    assert ".portal-shell--auth" in (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
    assert "[hidden] { display: none !important; }" in (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")


def test_ticket_and_payment_submissions_are_single_flight_and_idempotent_in_memory() -> None:
    assert "function acquireSubmission(scope, fingerprint)" in INTEGRATION
    assert "const submissions = new Map();" in INTEGRATION
    assert 'acquireSubmission("ticket", `${subject}\\n${detailText}`)' in INTEGRATION
    assert 'acquireSubmission("payment", packageId)' in INTEGRATION
    assert 'window.location.assign("/tickets");' in INTEGRATION


def test_job_asset_and_ticket_views_only_filter_redacted_canonical_metadata() -> None:
    assert "const ASSET_FILTERS" in PORTAL
    assert "const TICKET_FILTERS" in PORTAL
    assert "function jobCost(item)" in PORTAL
    assert "function ticketStatus(item)" in PORTAL
    assert 'data-portal-action="filter-assets"' not in PORTAL  # attributes are generated by filterBar
    assert 'filterBar(ASSET_FILTERS, selected, "filter-assets"' in PORTAL
    assert 'filterBar(TICKET_FILTERS, selected, "filter-tickets"' in PORTAL
    assert 'assetFilter: source.getAttribute("data-asset-filter")' in PORTAL
    assert 'ticketFilter: source.getAttribute("data-ticket-filter")' in PORTAL
    assert 'if (action === "filter-assets")' in INTEGRATION
    assert 'if (action === "filter-tickets")' in INTEGRATION


def test_admin_route_aliases_use_existing_read_only_bridge_modules() -> None:
    assert "const ADMIN_MODULE_ALIASES" in INTEGRATION
    assert 'backup: "backups", export: "reports"' in INTEGRATION
    assert "const ADMIN_CANONICAL_READ_MODULES" in INTEGRATION
    assert "function adminBridgeTargetForPath(path)" in INTEGRATION
    assert "function localAdminCompatibilityGuard(target)" in INTEGRATION
    assert "async function readAdminPath(path)" in INTEGRATION
    assert "return target.supported ? api(target.endpoint) : localAdminCompatibilityGuard(target);" in INTEGRATION
    assert "const admin = await readAdminPath(path);" in INTEGRATION
    assert "ADMIN_MODULE_ADAPTER_NOT_PUBLISHED" in INTEGRATION
    assert '"/admin/jobs/failed": "/admin/modules/failed-jobs"' in INTEGRATION
    assert '"/admin/providers": "/admin/modules/providers"' in INTEGRATION
    assert "compatibility_guarded" in PORTAL
    assert "Web không gọi một module Bot chưa công bố" in PORTAL
    assert '"Worker jobs"' in PORTAL
    assert 'adminPage("/admin/provider-cost"' in PORTAL
    assert 'adminPage("/admin/freezes"' in PORTAL
    assert 'adminPage("/admin/backups"' in PORTAL
    assert "const ADMIN_DIRECTORY_GROUPS" in PORTAL
    assert "function adminDirectoryEntries()" in PORTAL
    assert 'if (context.isAdmin !== true) return "";' in PORTAL
    assert "renderAdminDirectory(context)" in PORTAL
    assert "Danh mục Admin ERP" in PORTAL


def test_failed_job_incidents_are_read_only_and_show_only_redacted_canonical_triage_fields() -> None:
    assert 'if (module === "failed-jobs")' in PORTAL
    assert "Incident queue chỉ đọc" in PORTAL
    assert "error_category" in PORTAL
    assert "Chi phí / hoàn Xu" in PORTAL
    assert "retry, refund, charge và provider operation tiếp tục do Bot canonical quyết định" in PORTAL
    incident = PORTAL[PORTAL.index('if (module === "failed-jobs")'):PORTAL.index('if (["jobs", "failed-jobs", "workers", "runtime"].includes(module))')]
    assert "adminJobActions" not in incident
    assert "download_url" not in incident
    assert "provider_task" not in incident
    assert "const incidentReadOnly = module === \"failed-jobs\";" in PORTAL
    assert "Bot giữ retry/refund/charge" in PORTAL


def test_content_operations_admin_modules_are_explicit_navigation_not_browser_automation() -> None:
    for route, title in {
        "/admin/campaigns": "Campaign Center",
        "/admin/calendar": "Content Calendar",
        "/admin/approvals": "Approval Queue",
        "/admin/publishing": "Publishing & Channels",
        "/admin/analytics": "Analytics",
    }.items():
        assert f'adminPage("{route}", "{title}"' in PORTAL
        assert f'WebFeature("admin_{route.rsplit("/", 1)[-1]}", "{title}", "admin", "{route}", "admin")' in (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")
    assert 'key: "content-ops", title: "Content & Publishing"' in PORTAL
    assert 'return "content-ops";' in PORTAL
    section = PORTAL[PORTAL.index('adminPage("/admin/campaigns"'):PORTAL.index('adminPage("/admin/audit"')]
    assert 'action: "none"' not in section  # adminPage enforces this centrally rather than each declaration
    assert "không tự gửi bài" in section
    assert "không tạo hoặc publish lịch giả" in section
    assert "data-portal-action" not in section
    assert "payos" not in section.lower()
    assert "provider" not in section.lower()


def test_personal_web_memory_is_native_while_bot_companions_preserve_telegram_first_workflows() -> None:
    registry = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")
    for route, title in (
        ("/notes", "Memory Center"),
        ("/reminders", "Nhắc việc"),
    ):
        assert f'customerPage("{route}", "{title}"' in PORTAL
        assert f'botCompanionPage("{route}", ' not in PORTAL

    for route, key, title in (
        ("/referrals", "referrals", "Giới thiệu"),
        ("/rewards", "rewards", "Ưu đãi & quà"),
        ("/community", "community", "Cộng đồng"),
        ("/guides", "guides", "Hướng dẫn Bot"),
    ):
        assert f'botCompanionPage("{route}", "{title}"' in PORTAL
        assert f'WebFeature("{key}", "{title}", "account", "{route}"' in registry
    companion = PORTAL[PORTAL.index("function renderBotCompanion(page, context)"):PORTAL.index("function renderLanding(page, context)")]
    assert 'data-portal-action="copy-bot-companion-command"' in companion
    assert "Portal chỉ mở Bot hoặc sao chép một lệnh an toàn" in PORTAL
    assert "không nhân bản state" in companion
    assert "fetch(" not in companion
    assert "BOT_COMPANION_COMMANDS" in INTEGRATION
    assert "function copyBotCompanionCommand(value)" in INTEGRATION
    assert ".portal-bot-companion-grid" in PORTAL_CSS


def test_guarded_feature_handoffs_use_only_reviewed_zero_argument_bot_entry_commands() -> None:
    handoff = PORTAL[
        PORTAL.index("const FEATURE_BOT_HANDOFFS = Object.freeze({"):
        PORTAL.index("function copyFields(fields)")
    ]
    for feature, command in {
        "prompt_studio": "/film",
        "image_create": "/image_tools",
        "video_single": "/create_media",
        "music_background": "/music",
        "subtitle_create": "/translate",
        "documents": "/doc_tools",
    }.items():
        assert f'{feature}: Object.freeze({{ command: "{command}"' in handoff
        assert f'"{command}"' in INTEGRATION
    feature_handoff = PORTAL[
        PORTAL.index("function renderFeatureBotHandoff(page, context, flow)"):
        PORTAL.index("function renderWorkspace(page, context)")
    ]
    assert "const handoff = FEATURE_BOT_HANDOFFS[feature] || null;" in feature_handoff
    assert 'data-copy-text="${safeText(handoffCommand)}"' in feature_handoff
    assert "Không truyền prompt, upload ID, Telegram ID, quote, Xu, session hoặc token." in feature_handoff
    assert "fetch(" not in feature_handoff
    assert "/voiceover" not in handoff
    assert "Engine Web chưa bật" in feature_handoff
    assert "Bot companion (tùy chọn)" in feature_handoff
    contract = (ROOT / "docs" / "migration" / "BOT_COMPANION_HANDOFF.md").read_text(encoding="utf-8")
    assert "Feature-family handoff review (frozen Bot baseline)" in contract
    assert "that need a topic, file, transaction, job ID" in contract
    assert "not offered as Web copy controls" in contract


def test_customer_parity_hubs_split_membership_status_tools_and_media_navigation_from_dashboard() -> None:
    registry = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")
    expected = {
        "/membership": ("membership", "Gói thành viên"),
        "/status": ("service_status", "Trạng thái dịch vụ"),
        "/tools": ("tool_directory", "Công cụ & models"),
        "/studio": ("media_studio", "Media Studio"),
    }
    for route, (key, title) in expected.items():
        assert f'WebFeature("{key}", "{title}"' in registry
        assert f'customerPage("{route}", "{title}"' in PORTAL
    membership = PORTAL[PORTAL.index("function renderMembership(page, context)"):PORTAL.index("function renderServiceStatus(page, context)")]
    assert "Bot canonical" in membership
    assert "không tự cấp VIP" in membership
    assert "fetch(" not in membership
    assert "/api/v1/" not in membership
    service_status = PORTAL[PORTAL.index("function renderServiceStatus(page, context)"):PORTAL.index("function renderMediaStudio(page, context)")]
    assert "Telegram ID, code, callback token, HMAC secret" in service_status
    assert "bot_callback_observed" in service_status
    assert "fetch(" not in service_status
    media_studio = PORTAL[PORTAL.index("function renderMediaStudio(page, context)"):PORTAL.index("function safePayosCheckout(value)")]
    assert "Điều phối workflow, không giả project" in media_studio
    assert "Không tạo job tại browser" in media_studio
    assert "fetch(" not in media_studio
    assert 'case "membership": return renderMembership(page, context);' in PORTAL
    assert 'case "service-status": return renderServiceStatus(page, context);' in PORTAL
    assert 'case "media-studio": return renderMediaStudio(page, context);' in PORTAL
    assert 'path === "/membership"' in INTEGRATION
    assert 'api("/wallet"), api("/packages"), api("/features/status")' in INTEGRATION
    contract = (ROOT / "docs" / "migration" / "FEATURE_FAMILY_NAVIGATION.md").read_text(encoding="utf-8")
    assert "Customer parity hubs" in contract
    assert "`/membership`" in contract
    assert "`/status`" in contract
    assert "`/tools`" in contract
    assert "`/studio`" in contract


def test_registration_copy_does_not_claim_unimplemented_email_verification() -> None:
    assert "email verification được Core Bridge thực thi" not in PORTAL
    assert "response đăng ký không tiết lộ email đã có tài khoản hay chưa" in PORTAL
    assert "Chỉ đăng nhập Email + mật khẩu hoặc OAuth đã xác thực mới cấp signed session và CSRF" in PORTAL


def test_login_methods_are_explicit_about_telegram_gmail_and_configuration_gated_oauth() -> None:
    assert 'label: "Email (có thể dùng Gmail)"' in PORTAL
    assert "function renderTelegramLoginMethod(context)" in PORTAL
    assert "Không nhập Telegram ID vào Web" in PORTAL
    assert "Telegram Login xác thực Web bằng OIDC" in PORTAL
    assert 'renderPublicOAuthCard("telegram", "Telegram Login", telegramOidcEnabled, "✈", "signin")' in PORTAL
    assert 'data-portal-action="start-telegram-login"' in PORTAL
    assert 'data-portal-action="refresh-telegram-login"' in PORTAL
    assert "Google (OAuth)" in PORTAL
    assert "GitHub" in PORTAL
    assert "Sign in with Apple" in PORTAL
    assert "OAuth chưa được cấu hình trên server" in PORTAL
    assert "không có đăng nhập giả" in PORTAL
    assert 'window.location.assign("/login?registered=1");' in INTEGRATION
    assert 'api("/auth/telegram/login/start"' in INTEGRATION
    assert 'api("/auth/telegram/login/complete"' in INTEGRATION
    assert 'fetch(`${API}/auth/telegram/connection/status`' in INTEGRATION
    assert "function telegramConnectionReady(connection)" in INTEGRATION
    assert "connection.ready === true" in INTEGRATION
    assert "connection.bot_callback_adapter_enabled" in PORTAL
    assert "Web sẽ không tạo mã chết" in PORTAL
    assert "bot_callback_observed" in PORTAL
    assert "Telegram ID không đi qua browser" in PORTAL
    assert '"start-telegram-login": telegramReady' in INTEGRATION
    assert '"start-telegram-link": Boolean(account && telegramReady)' in INTEGRATION
    assert 'fetch(`${API}/auth/providers`' in INTEGRATION
    assert "function safeOAuthStartPath(value)" in INTEGRATION
    assert "telegram|google|github|apple" in INTEGRATION
    assert 'api(`/auth/oauth/${provider}/link/start`' in INTEGRATION
    assert "_telegram_login_cookie_value" in (ROOT / "copyfast_auth.py").read_text(encoding="utf-8")


def test_telegram_onboarding_can_start_from_a_fresh_signed_web_account() -> None:
    """The no-code onboarding state must not trap a new email/OAuth account."""
    onboarding = PORTAL[PORTAL.index("function renderOnboarding(page, context)"):PORTAL.index("function renderPublicOAuthCard(provider")]
    assert 'renderEmpty("Chưa có mã liên kết"' in onboarding
    assert 'data-portal-action="start-telegram-link"' in onboarding
    assert "Tạo mã liên kết Telegram" in onboarding
    assert 'data-portal-action="copy-telegram-link-command"' in onboarding
    assert "function copyTelegramLinkCommand(value)" in INTEGRATION
    assert 'action === "copy-telegram-link-command"' in INTEGRATION


def test_account_exposes_bot_preferences_only_as_safe_handoffs() -> None:
    account = PORTAL[PORTAL.index("function renderAccount(page, context)"):PORTAL.index("function renderLegal(page, context)")]
    assert "Tuỳ chọn do Bot quản lý" in account
    assert 'command: "/language"' in account
    assert 'command: "/mode"' in account
    assert 'command: "/profile"' in account
    assert 'command: "/mydata"' in account
    assert 'command: "/data_delete"' in account
    assert 'data-portal-action="copy-bot-companion-command"' in account
    assert "Web không giả đồng bộ" in account
    assert "Xóa dữ liệu, đổi quyền hay thay Telegram identity" in account
    assert "fetch(" not in account
    assert '"/language", "/mode", "/profile", "/mydata"' in INTEGRATION
    assert '"/tickets", "/ticket_status", "/data_delete"' in INTEGRATION
    handoff = (ROOT / "docs" / "migration" / "BOT_COMPANION_HANDOFF.md").read_text(encoding="utf-8")
    assert "`/language`, `/mode`, `/profile`, `/mydata`" in handoff
    assert "`/data_delete`" in handoff


def test_ticket_bot_handoff_never_moves_a_ticket_thread_or_identifier_to_telegram() -> None:
    tickets = PORTAL[PORTAL.index("function renderTickets(page, context)"):PORTAL.index("function renderAccount(page, context)")]
    assert "Theo dõi sâu trong Bot" in tickets
    assert 'data-copy-text="/tickets"' in tickets
    assert 'data-copy-text="/ticket_status"' in tickets
    handoff = tickets[tickets.index("const ticketBotHandoff"):tickets.index("return `<article", tickets.index("const ticketBotHandoff"))]
    assert "không gửi mã ticket, identity" in handoff
    assert "item.id" not in handoff
    assert "fetch(" not in handoff


def test_growth_and_campaign_reports_use_the_real_bot_handoff_until_a_report_adapter_exists() -> None:
    assert 'analyticsBotCompanionPage("/growth/ai", "Growth AI"' in PORTAL
    assert 'analyticsBotCompanionPage("/campaign/report", "Báo cáo campaign"' in PORTAL
    assert 'layout: "analytics-bot-companion"' in PORTAL
    analytics = PORTAL[PORTAL.index("function renderAnalyticsBotCompanion(page, context)"):PORTAL.index("function renderLanding(page, context)")]
    assert 'data-portal-action="copy-analytics-bot-command"' in analytics
    assert 'name="campaign_id"' in analytics
    assert 'name="goal"' in analytics
    assert 'name="format"' in analytics
    assert "Không có request analytics, Xu hay file nào gửi từ browser." in analytics
    assert "fetch(" not in analytics
    assert 'const ANALYTICS_BOT_COMMANDS = new Set(["/growth_ai", "/campaign_report"])' in INTEGRATION
    assert "function buildAnalyticsBotCommand(fields)" in INTEGRATION
    assert "function copyAnalyticsBotCommand(fields)" in INTEGRATION
    assert 'action === "copy-analytics-bot-command"' in INTEGRATION
    assert "ANALYTICS_BOT_PLATFORMS" in INTEGRATION
    assert "ANALYTICS_BOT_GOALS" in INTEGRATION
    assert "ANALYTICS_BOT_FORMATS" in INTEGRATION
    assert "không tự tính doanh thu, performance hay tạo file xuất giả" in PORTAL
    contract = (ROOT / "docs" / "migration" / "FEATURE_FAMILY_NAVIGATION.md").read_text(encoding="utf-8")
    assert "/growth/ai" in contract
    assert "/campaign/report" in contract
    assert "tightly allowlisted Bot command" in contract
    handoff = (ROOT / "docs" / "migration" / "BOT_COMPANION_HANDOFF.md").read_text(encoding="utf-8")
    assert "separate closed schema" in handoff
    assert "The Portal does not read performance data" in handoff


def test_telegram_onboarding_preserves_only_a_safe_local_workflow_continuation() -> None:
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "def _safe_onboarding_next(value: str | None)" in app
    assert 'candidate.startswith("//")' in app
    assert "parsed.scheme or parsed.netloc or parsed.params or parsed.query or parsed.fragment" in app
    assert "_safe_onboarding_next(request.query_params.get(\"next\")) or \"/dashboard\"" in app
    assert "function safeReturnPath(value)" in INTEGRATION
    assert "function requestedPortalRoute()" in INTEGRATION
    assert 'window.location.assign(requested || "/dashboard");' in INTEGRATION
    assert "function safeOnboardingContinuation(value)" in PORTAL
    assert "function onboardingContinuationRoute()" in PORTAL
    assert "Workflow đang chờ" in PORTAL
    assert "Mở lại workflow" in PORTAL
    continuation = PORTAL[PORTAL.index("function safeOnboardingContinuation(value)"):PORTAL.index("function renderPublicOAuthCard(provider")]
    assert "/api/v1/" not in continuation
    assert 'href="/payments' not in continuation
    assert "localStorage." not in continuation
    assert "telegram_id" not in continuation
    oauth_card = PORTAL[PORTAL.index("function renderPublicOAuthCard(provider"):PORTAL.index("function renderTelegramLoginMethod(context)")]
    assert "const continuation = onboardingContinuationRoute();" in oauth_card
    assert "?next=${encodeURIComponent(continuation)}" in oauth_card
    assert "const startPath" in oauth_card
    auth = (ROOT / "copyfast_auth.py").read_text(encoding="utf-8")
    assert "return_path = _safe_oauth_return_path(state_data[\"return_path\"])" in auth
    assert "target = return_path" in auth
    assert "response = RedirectResponse(target" in auth


def test_legacy_raw_telegram_login_shells_are_redirected_to_the_signed_portal() -> None:
    legacy_login = (ROOT / "login.html").read_text(encoding="utf-8")
    assert 'url=/login' in legacy_login
    assert "telegram-id" not in legacy_login
    assert "localStorage" not in legacy_login
    assert "user_id" not in legacy_login
    legacy_wallet = (ROOT / "wallet.html").read_text(encoding="utf-8")
    legacy_wallet_script = (ROOT / "wallet.js").read_text(encoding="utf-8")
    assert 'url=/wallet' in legacy_wallet
    assert "localStorage" not in legacy_wallet
    assert "create-payment-link" not in legacy_wallet
    assert "localStorage" not in legacy_wallet_script
    assert "create-payment-link" not in legacy_wallet_script
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '"/login.html": "/login"' in app
    assert '"/auth.html": "/login"' in app
    assert "_legacy_html_redirects" in app
    assert "function renderTelegramConnectionNotice(context)" in PORTAL
    assert "connectionDisabled" in PORTAL
    compatibility_main = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "from app import app" in compatibility_main
    assert "include_router" not in compatibility_main


def test_normalized_portal_context_keeps_hydrated_oauth_telegram_and_payment_state() -> None:
    """Async integration state must survive the next render, not just merge()."""
    assert 'oauthProviders: source.oauthProviders && typeof source.oauthProviders === "object" ? source.oauthProviders : {}' in PORTAL
    assert 'telegramLoginFlow: source.telegramLoginFlow && typeof source.telegramLoginFlow === "object" ? source.telegramLoginFlow : {}' in PORTAL
    assert 'paymentOptions: source.paymentOptions && typeof source.paymentOptions === "object" ? source.paymentOptions : {}' in PORTAL


def test_account_profile_editor_only_targets_web_owned_defaults() -> None:
    assert 'data-portal-action="update-profile"' in PORTAL
    assert "Tuỳ chỉnh hồ sơ Web" in PORTAL
    assert "Telegram identity, role, Xu, PayOS và provider" in PORTAL
    assert '"update-profile": Boolean(account && me.csrf_token)' in INTEGRATION
    assert 'api("/auth/profile"' in INTEGRATION
    auth = (ROOT / "copyfast_auth.py").read_text(encoding="utf-8")
    assert "class ProfileUpdateRequest(BaseModel):" in auth
    assert "def update_profile" in auth
    assert "PROFILE_TIMEZONE_INVALID" in auth
    assert "web_account_profiles" in (ROOT / "copyfast_db.py").read_text(encoding="utf-8")


def test_feature_planning_state_is_distinguished_from_provider_engine_readiness() -> None:
    assert "const planningAvailable = Boolean(" in PORTAL
    assert "Web Studio đã sẵn sàng; engine vẫn được bảo vệ" in PORTAL
    assert "Web App đang chờ adapter tạo job canonical" in PORTAL
    assert "function featureConfirmExecutionReady(page, context)" in PORTAL
    assert "featureExecutionFeatures" in PORTAL
    assert "state.public_ready && allowed.has(key)" in INTEGRATION
    assert "draftReady = Boolean(authoringReady && draftFeatures.has(key))" in INTEGRATION
    assert "featureExecutionAllowed(feature)" in INTEGRATION
    assert '"feature-confirm": webFeatureExecutionAvailable' in INTEGRATION


def test_guarded_feature_execution_keeps_web_authoring_primary_and_bot_companion_optional() -> None:
    assert "function renderFeatureBotHandoff(page, context, flow)" in PORTAL
    handoff = PORTAL[PORTAL.index("function renderFeatureBotHandoff(page, context, flow)"):PORTAL.index("function renderWorkspace(page, context)")]
    assert "Engine Web chưa bật" in handoff
    assert "Bot companion (tùy chọn)" in handoff
    assert "Mở Project Center" in handoff
    assert 'const handoffCommand = handoff ? handoff.command : "/menu";' in handoff
    assert 'data-copy-text="${safeText(handoffCommand)}"' in handoff
    assert "Không có" in handoff
    assert "không truyền prompt, upload ID, Telegram ID, quote, Xu, session hoặc token" in handoff
    assert "fetch(" not in handoff
    assert "/api/v1/" not in handoff
    assert "${renderFeatureBotHandoff(page, context, flow)}" in PORTAL
    contract = (ROOT / "docs" / "migration" / "FEATURE_CONFIRM_CONTRACT.md").read_text(encoding="utf-8")
    assert "Optional Bot-companion continuation" in contract
    assert "customer in Web authoring" in contract


def test_support_form_does_not_silently_drop_a_file_attachment() -> None:
    assert 'name: "attachment"' not in PORTAL
    assert "form hiện tại không nhận hoặc bỏ qua file" in PORTAL
    assert "validateSupportIntake(subject, detailText)" in INTEGRATION
    assert "Ticket không nhận API key, token" in INTEGRATION


def test_admin_writes_are_explicitly_flag_gated_confirmed_and_idempotent() -> None:
    assert 'action: "none"' in PORTAL
    assert "Chế độ chỉ đọc" in PORTAL
    assert "function adminJobActions(item, context, route)" in PORTAL
    assert 'data-portal-action="admin-retry"' in PORTAL
    assert 'data-portal-action="admin-refund"' in PORTAL
    assert 'data-portal-action="admin-freeze"' in PORTAL
    assert "data-portal-confirm=\"Retry job" in PORTAL
    assert "Yêu cầu hoàn Xu cho job" in PORTAL
    assert "Maintenance feature canonical" in PORTAL
    assert "WEBAPP_ADMIN_WRITES_ENABLED" in PORTAL
    assert '"admin-retry": adminWriteEnabled' in INTEGRATION
    assert '"admin-refund": adminWriteEnabled' in INTEGRATION
    assert '"admin-freeze": adminWriteEnabled' in INTEGRATION
    assert "function validAdminJobId(value)" in INTEGRATION
    assert "function validAdminFeatureKey(value)" in INTEGRATION
    assert "const scope = `admin:${operation}:${jobId}`;" in INTEGRATION
    assert "const scope = `admin:freeze:${feature}`;" in INTEGRATION
    assert "acquireSubmission(scope," in INTEGRATION
    assert "function discardSubmission(scope, entry)" in INTEGRATION
    assert "if (acknowledged) discardSubmission(scope, submission);" in INTEGRATION
    assert "status.flags.admin_erp_enabled === true" in INTEGRATION
    assert "`/admin/jobs/${encodeURIComponent(jobId)}/${operation}`" in INTEGRATION
    assert "`/admin/features/${encodeURIComponent(feature)}/freeze`" in INTEGRATION
    api = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    assert "require_admin_csrf(request)" in api
    assert "await require_canonical_admin_csrf(request)" in api
    assert '"WEBAPP_ADMIN_WRITES_ENABLED", False' in api
    assert '"WEBAPP_ADMIN_ERP_ENABLED"' in api
    assert "def require_operation_note" in api
    assert '"failed_no_charge"' in PORTAL


def test_admin_erp_can_render_canonical_user_references_only_after_server_role_check() -> None:
    api = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    assert 'account: dict = Depends(require_canonical_admin)' in api
    assert 'request=request, admin_read=True' in api
    assert 'allow_admin_user_refs and normalized in {"userid", "username"}' in api
    assert '"canonicaluserid"' in api


def test_voice_output_preview_and_history_views_do_not_overclaim_unmapped_delivery() -> None:
    assert 'guardedFeaturePage("/voice/outputs"' in PORTAL
    assert 'path === "/voice/outputs"' in INTEGRATION
    assert '"/voice/outputs", "/music/library"' not in INTEGRATION
    assert "Có preview canonical · chờ adapter URL ký" in PORTAL
    assert "consent_status" in PORTAL
    assert "tối đa 100" in PORTAL


def test_ticket_statuses_and_categories_match_the_bot_support_contract() -> None:
    for status in ("waiting_user", "waiting_provider", "refund_pending", "resolved", "closed"):
        assert f'"{status}"' in PORTAL
        assert f'"{status}"' in INTEGRATION
    assert "function canonicalTicketStatus(item)" in PORTAL
    assert "function ticketCategoryLabel(item)" in PORTAL
    assert "web_ticket: \"Hỗ trợ Web\"" in PORTAL


def test_telegram_deep_links_and_session_metadata_stay_browser_safe() -> None:
    assert "function safeTelegramLink(value)" in PORTAL
    telegram_link_slice = PORTAL[PORTAL.index("function safeTelegramLink(value)"):PORTAL.index("function renderOnboarding")]
    assert 'url.hostname === "t.me"' in telegram_link_slice
    assert "url.hostname.endsWith" not in telegram_link_slice
    assert "telegram_linked" in INTEGRATION
    assert "account.canonical_user_id" not in INTEGRATION


def test_telegram_one_time_challenges_auto_resume_only_in_the_same_visible_browser_session() -> None:
    assert "const TELEGRAM_CHALLENGE_POLL_INTERVAL_MS = 2500;" in INTEGRATION
    assert "function telegramChallengePending(flow)" in INTEGRATION
    assert "function portalIsVisible()" in INTEGRATION
    assert "function stopTelegramLoginPolling()" in INTEGRATION
    assert "function stopTelegramLinkPolling()" in INTEGRATION
    assert "async function refreshTelegramLoginChallenge" in INTEGRATION
    assert "async function refreshTelegramLinkChallenge" in INTEGRATION
    assert "function scheduleTelegramLoginPolling(delayMs)" in INTEGRATION
    assert "function scheduleTelegramLinkPolling(delayMs)" in INTEGRATION
    assert "scheduleTelegramLoginPolling();" in INTEGRATION
    assert "scheduleTelegramLinkPolling();" in INTEGRATION
    assert 'window.addEventListener("visibilitychange"' in INTEGRATION
    challenge_slice = INTEGRATION[INTEGRATION.index("function telegramChallengePending(flow)"):INTEGRATION.index("function supportSensitiveContentKind")]
    assert "localStorage" not in challenge_slice
    assert "telegram_id" not in challenge_slice
    assert 'api("/auth/telegram/login/complete"' in INTEGRATION
    assert 'api("/auth/telegram/link/status")' in INTEGRATION


def test_telegram_link_recovery_never_restores_a_code_and_requires_browser_completion() -> None:
    assert "async function resumeTelegramLinkChallenge" in INTEGRATION
    assert "async function completeTelegramLinkChallenge" in INTEGRATION
    assert 'api("/auth/telegram/link/complete"' in INTEGRATION
    assert "ready_to_complete" in INTEGRATION
    assert "recoverTelegramLinkFlow" in INTEGRATION
    assert "telegramLinkResumeProbeInFlight" in INTEGRATION
    assert "renderRecoveredTelegramLinkChallenge" in PORTAL
    assert "Mã liên kết đã hết hạn" in PORTAL
    assert "renderExpiredTelegramLoginChallenge" in PORTAL
    assert "TELEGRAM_LOGIN_EXPIRED" in INTEGRATION
    assert "telegramConnectionBlockReason" in PORTAL
    assert "Web không tạo mã chết" in PORTAL
    recovery_slice = INTEGRATION[INTEGRATION.index("async function resumeTelegramLinkChallenge"):INTEGRATION.index("function scheduleTelegramLoginPolling")]
    assert "localStorage" not in recovery_slice
    assert "canonical_user_id" not in recovery_slice
    assert "data.code =" not in recovery_slice


def test_feature_workspace_uses_only_explicit_tracking_references_and_never_infers_jobs() -> None:
    assert "const FEATURE_TRACKING_JOB_STATES" in PORTAL
    assert "function safeFeatureTracking(flow)" in PORTAL
    assert "function renderFeatureTracking(flow)" in PORTAL
    assert "feature !== expectedFeature" in PORTAL
    assert "flowStatus !== status" in PORTAL
    assert 'href="/jobs"' in PORTAL
    assert 'const href = `/jobs/${encodeURIComponent(tracking.id)}`;' in PORTAL
    assert "Không ghép job theo thời gian hoặc tên feature" in PORTAL
    assert "${renderFeatureTracking(flow)}" in PORTAL
    api = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    assert "def _project_feature_tracking" in api
    assert "feature != expected" in api
    assert "status not in FEATURE_CONFIRM_ACCEPTED_STATUSES" in api
    assert 'result["tracking"] = tracking' in api


def test_canonical_planning_can_be_reused_only_as_ephemeral_safe_form_text() -> None:
    """Bot planning can speed up intake without turning into a provider action.

    These browser-only actions deliberately accept bounded text, copy it or
    place it into an existing declared text field.  They must never persist a
    Bot response in local storage or target uploads, amounts or select
    controls where an inferred value could alter a canonical workflow.
    """
    assert "function canonicalDraftText(value)" in PORTAL
    assert "function featureDraftTarget(flow, route)" in PORTAL
    assert "function canonicalDraftActions(text, route, field, label)" in PORTAL
    assert "function renderCanonicalSuggestions(value, route, field)" in PORTAL
    assert 'data-portal-action="copy-canonical-draft"' in PORTAL
    assert 'data-portal-action="apply-canonical-draft"' in PORTAL
    assert "function copyCanonicalDraftText(value)" in PORTAL
    assert "function applyCanonicalDraftToForm(route, field, value)" in PORTAL
    assert "Chưa gọi provider · Chưa trừ Xu." in PORTAL
    assert ".portal-suggestion-grid" in PORTAL_CSS
    assert ".portal-canonical-actions" in PORTAL_CSS

    apply_action = PORTAL[
        PORTAL.index("function applyCanonicalDraftToForm(route, field, value)"):
        PORTAL.index("function dispatchAction(source, context)")
    ]
    assert "transientFormDrafts.set" in apply_action
    assert "localStorage" not in apply_action
    assert '["file", "checkbox", "number"]' in apply_action
    assert 'definition.control === "select"' in apply_action
    assert "data-canonical-route" in PORTAL
    assert "data-canonical-field" in PORTAL
    assert "data-canonical-text" in PORTAL


def test_welcome_is_an_explicit_marketing_route_while_root_stays_in_app_mode() -> None:
    assert 'customerPage("/welcome", "TOAN AAS"' in PORTAL
    assert 'access: "public", layout: "landing", action: "none", status: "ready"' in PORTAL
    assert "function customerPage(path, title, description, icon, extra, aliases)" in PORTAL
    assert '}, ["/app"]);' in PORTAL
    assert "function renderLanding(page, context)" in PORTAL
    assert 'case "landing": return renderLanding(page, context);' in PORTAL
    assert "Không tạo output giả" in PORTAL
    assert "Project &amp; Studio Document Web-owned" in PORTAL
    assert "Telegram companion là tùy chọn" in PORTAL
    landing = PORTAL[
        PORTAL.index("function renderLanding(page, context)"):
        PORTAL.index("function renderNotFound(page, context)")
    ]
    assert "/api/v1/" not in landing
    assert "fetch(" not in landing
    assert "localStorage" not in landing
    assert "Không có ledger Xu, webhook PayOS" in landing
    assert 'href: "/login?next=/video/create"' in landing
    assert 'id="studios"' in landing
    assert 'id="workflow"' in landing
    assert 'id="trust"' in landing
    assert "portal-shell--landing" in PORTAL
    assert "sidebar.hidden = minimalShell;" in PORTAL
    assert "header.hidden = minimalShell;" in PORTAL
    assert ".portal-shell--landing" in PORTAL_CSS
    assert ".portal-landing-studios" in PORTAL_CSS
    assert ".portal-landing-preview" in PORTAL_CSS
    assert "scroll-snap-type: x mandatory" in PORTAL_CSS
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'if normalized in {"/", "/app"}:' in app
    assert 'return RedirectResponse("/login", status_code=307)' in app
    assert 'return RedirectResponse("/dashboard", status_code=307)' in app
    assert 'public_pages = {"/welcome", "/legal", "/privacy"}' in app
    railway = (ROOT / "railway.json").read_text(encoding="utf-8")
    assert '"healthcheckPath": "/health"' in railway


def test_dashboard_uses_an_application_workspace_shell_with_owner_scoped_drafts() -> None:
    assert "function renderDashboardWorkspaceSummary(context)" in PORTAL
    assert "function renderDashboardRecentDrafts(context)" in PORTAL
    assert 'class="portal-page portal-dashboard-app"' in PORTAL
    assert 'class="portal-dashboard-overview"' in PORTAL
    assert 'class="portal-dashboard-draft-list"' in PORTAL
    assert 'class="portal-sidebar-create" href="/features"' in PORTAL
    assert 'label: "Bot companion"' in PORTAL
    assert 'label: "Workspace"' in PORTAL
    assert '["/workspace", "/dashboard"].includes(currentPath)' in INTEGRATION
    for selector in (".portal-dashboard-overview", ".portal-dashboard-draft", ".portal-sidebar-create"):
        assert selector in PORTAL_CSS


def test_browser_idempotency_keys_normalize_route_scopes_to_the_server_contract() -> None:
    """A safe draft save must not fail merely because its route contains `/`."""
    assert "function randomKey(prefix)" in INTEGRATION
    assert '.replace(/[^A-Za-z0-9._:-]+/g, "-")' in INTEGRATION
    assert '.replace(/^-+|-+$/g, "")' in INTEGRATION
    assert ".slice(0, 120) || \"web\"" in INTEGRATION
    assert 'const scope = updating ? `workspace-draft:${draftId}:update` : `workspace-draft:${feature.key}:${route}:create`;' in INTEGRATION
    api = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    assert 'IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")' in api


def test_video_finalization_maps_bot_navigation_without_faking_mux_or_delivery() -> None:
    assert "function guidedFeaturePage(path, title, description, icon, layout, aliases, notes)" in PORTAL
    assert 'guidedFeaturePage("/video/add-ons", "Video finalization"' in PORTAL
    assert 'guidedFeaturePage("/video/mux", "Mux audio & video"' in PORTAL
    assert "function renderVideoFinalization(page, context)" in PORTAL
    assert 'case "video-finalization": return renderVideoFinalization(page, context);' in PORTAL
    finalization = PORTAL[
        PORTAL.index("function renderVideoFinalization(page, context)"):
        PORTAL.index("function renderNotFound(page, context)")
    ]
    for href in ("/voice/tts", "/music/create", "/dubbing", "/subtitle", "/jobs", "/assets", "/video/preview"):
        assert f'href: "{href}"' in finalization
    assert "Không tự gọi FFmpeg/provider" in finalization
    assert "Không trừ Xu ở browser" in finalization
    assert "Không tạo delivery giả" in finalization
    assert "data-portal-action" not in finalization
    assert "fetch(" not in finalization
    assert ".portal-finalization-grid" in PORTAL_CSS
    assert ".portal-finalization-card.is-guarded" in PORTAL_CSS


def test_campaign_planner_is_a_web_owned_account_scoped_board_not_bot_campaign_automation() -> None:
    assert 'customerPage("/campaigns", "Campaign Planner"' in PORTAL
    assert 'layout: "campaign-planner", action: "campaign-create"' in PORTAL
    assert 'case "campaign-planner": return renderCampaignPlanner(page, context);' in PORTAL
    assert 'case "campaign-detail": return renderCampaignDetail(page, context);' in PORTAL
    local_actions = PORTAL[PORTAL.index("const WEB_LOCAL_ACTIONS = new Set(["):PORTAL.index("]);", PORTAL.index("const WEB_LOCAL_ACTIONS = new Set(["))]
    for action in ("campaign-create", "campaign-update", "campaign-update-status"):
        assert f'"{action}"' in local_actions
    assert "function renderCampaignPlanner(page, context)" in PORTAL
    assert "function renderCampaignDetail(page, context)" in PORTAL
    assert "function campaignPlanHref(plan)" in PORTAL
    assert "function campaignDestinationLink(value)" in PORTAL
    assert "target=\"_blank\" rel=\"noopener noreferrer\"" in PORTAL
    planner = PORTAL[
        PORTAL.index("function renderCampaignPlanner(page, context)"):
        PORTAL.index("function renderLanding(page, context)")
    ]
    assert "Campaign Planner chỉ lưu metadata" in PORTAL
    assert "không tự publish" in planner
    assert "không tạo analytics/revenue" in planner
    assert "Không gọi Bot, PayOS, Xu hay provider" in planner
    assert "fetch(" not in planner
    assert "localStorage" not in planner
    assert "/api/v1/" not in planner

    assert 'api("/campaigns")' in INTEGRATION
    assert 'if (action === "campaign-create")' in INTEGRATION
    assert 'if (action === "campaign-update")' in INTEGRATION
    assert 'if (action === "campaign-update-status")' in INTEGRATION
    assert "function campaignCreatePayload(fields)" in INTEGRATION
    assert "function campaignStatusPayload(fields)" in INTEGRATION
    assert "function campaignPlanIdFromPath(path)" in INTEGRATION
    assert "async function hydrateCampaignPlanDetail(path)" in INTEGRATION
    assert 'api(`/campaigns/${encodeURIComponent(planId)}`)' in INTEGRATION
    campaign_integration = INTEGRATION[
        INTEGRATION.index("function campaignCreatePayload(fields)"):
        INTEGRATION.index("function estimateCanAdvanceToConfirm")
    ]
    assert "https:" in campaign_integration
    assert "canonical_user_id" not in campaign_integration
    assert "provider" not in campaign_integration.lower()
    assert "payos" not in campaign_integration.lower()

    api = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    db = (ROOT / "copyfast_db.py").read_text(encoding="utf-8")
    assert 'CREATE TABLE IF NOT EXISTS web_campaign_plans' in db
    assert '@router.get("/campaigns")' in api
    assert '@router.get("/campaigns/{plan_id}")' in api
    assert '@router.post("/campaigns")' in api
    assert '@router.patch("/campaigns/{plan_id}")' in api
    assert '@router.post("/campaigns/{plan_id}/status")' in api
    assert "WHERE account_id=?" in api
    assert "WHERE id=? AND account_id=?" in api
    assert "campaign.plan.create" in api
    assert "campaign.plan.update" in api
    assert "campaign.plan.status" in api
    assert "web-local planning record created" in api
    assert "CAMPAIGN_PLAN_TRANSITIONS" in api

    app = (ROOT / "app.py").read_text(encoding="utf-8")
    pages = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
    assert '"/campaign.html": "/campaigns"' in app
    assert 'RedirectResponse("/campaigns", status_code=307)' in app
    assert '"/campaigns": "Campaign Planner"' in pages
    assert ".portal-campaign-board" in PORTAL_CSS
    assert ".portal-campaign-timeline" in PORTAL_CSS
    assert ".portal-campaign-edit" in PORTAL_CSS
    assert 'customerPage("/calendar", "Content Calendar"' in PORTAL
    assert 'customerPage("/approvals", "Self-review Queue"' in PORTAL
    assert 'case "campaign-calendar": return renderCampaignCalendar(page, context);' in PORTAL
    assert 'case "campaign-approvals": return renderCampaignApprovals(page, context);' in PORTAL
    assert "function renderCampaignCalendar(page, context)" in PORTAL
    assert "function renderCampaignApprovals(page, context)" in PORTAL
    calendar = PORTAL[
        PORTAL.index("function renderCampaignCalendar(page, context)"):
        PORTAL.index("function renderCampaignApprovals(page, context)")
    ]
    approvals = PORTAL[
        PORTAL.index("function renderCampaignApprovals(page, context)"):
        PORTAL.index("function renderLanding(page, context)")
    ]
    assert "Calendar không tạo publish queue" in calendar
    assert "Không reminder tự động" in calendar
    assert "Self-review Queue của riêng bạn" in approvals
    assert "Không có admin approval giả" in approvals
    assert "fetch(" not in calendar + approvals
    assert "localStorage" not in calendar + approvals
    assert '"/calendar": "Content Calendar"' in pages
    assert '"/approvals": "Self-review Queue"' in pages
    assert '["/campaigns", "/calendar", "/approvals"].includes(currentPath)' in INTEGRATION
    assert ".portal-calendar-grid" in PORTAL_CSS
    assert ".portal-calendar-event" in PORTAL_CSS
