"""Focused portal contracts for the Web-native AI Chat Workspace.

The UI must remain a private authoring application rather than reintroducing
the old generic `/chat` Core Bridge estimate surface or pretending to run AI.
"""

from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "copyfast_chat_workspace.py").read_text(encoding="utf-8")


def _chat_surface() -> str:
    start = PORTAL.index("const CHAT_WORKSPACE_MODES")
    return PORTAL[start:PORTAL.index("const DOCUMENT_WORKSPACE_TYPES", start)]


def _chat_helpers() -> str:
    start = INTEGRATION.index("const CHAT_WORKSPACE_MODES")
    return INTEGRATION[start:INTEGRATION.index("const DOCUMENT_WORKSPACE_TYPES", start)]


def test_chat_is_native_route_family_not_generic_bridge_estimate() -> None:
    for needle in (
        'customerPage("/chat"',
        'customerPage("/chat/new"',
        'path: "/chat/:id"',
        "function renderChatWorkspace(",
        "function renderChatWorkspaceDetail(",
        'case "chat-workspace": return renderChatWorkspace(page, context);',
        'case "chat-workspace-detail": return renderChatWorkspaceDetail(page, context);',
        'if (linkPath === "/chat") return matchesRouteFamily(path, "/chat")',
        "CHAT_WORKSPACE_PATH",
        "CHAT_WORKSPACE_PATH.fullmatch(normalized)",
    ):
        assert needle in (PAGES if "CHAT_WORKSPACE" in needle else PORTAL)

    assert 'featurePage("/chat"' not in PORTAL
    assert '"/chat": "chat"' not in INTEGRATION
    assert "function isNativeChatWorkspacePath(" in INTEGRATION
    assert "chatThreadIdFromPath(currentPath)" in INTEGRATION
    assert "else if (isNativeChatWorkspacePath(currentPath))" in INTEGRATION


def test_chat_authoring_boundary_is_explicit_in_ui_and_client_validation() -> None:
    helpers = _chat_helpers()
    for helper in (
        "chatWorkspaceSafetyError",
        "chatThreadPayload",
        "chatContextPayload",
        "chatTurnPayload",
        "chatWorkspaceBoundaryIsSafe",
    ):
        assert f"function {helper}" in helpers
    for boundary_flag in (
        'boundary.execution === "authoring_only"',
        "boundary.ai_execution_available === false",
        "boundary.provider_called === false",
        "boundary.bot_called === false",
        "boundary.assistant_reply_created === false",
        "boundary.output_created === false",
        "boundary.job_created === false",
        "boundary.wallet_mutated === false",
        "boundary.payment_processed === false",
        "boundary.browser_file_upload === false",
        "boundary.stream_available === false",
        'boundary.output_delivery === "guarded"',
    ):
        assert boundary_flag in helpers

    surface = _chat_surface()
    # The authoring surface is explicit that a thread is not model execution.
    # The wording can evolve, but it must retain this visible boundary.
    assert "Lưu thread không gọi AI hoặc trừ Xu." in surface
    assert "không phải model" in surface
    assert "không tạo câu trả lời giả" in surface
    for forbidden in (
        "fetch(",
        "api(",
        "localStorage",
        'data-portal-action="chat-workspace-execute"',
        'data-portal-action="chat-workspace-estimate"',
        'data-portal-action="chat-workspace-confirm"',
        'data-portal-action="chat-workspace-download"',
        'data-chat-role="assistant"',
        "data-chat-typing",
        "portal-chat-assistant",
    ):
        assert forbidden not in surface


def test_chat_mutations_are_signed_redacted_and_rehydrate_after_receipts() -> None:
    actions = (
        "chat-workspace-refresh",
        "chat-workspace-filter",
        "chat-workspace-page",
        "chat-thread-create",
        "chat-thread-update",
        "chat-thread-lifecycle",
        "chat-thread-restore-version",
        "chat-context-create",
        "chat-context-update",
        "chat-context-state",
        "chat-turn-create",
        "chat-turn-state",
    )
    for action in actions:
        assert f'action === "{action}"' in INTEGRATION
        assert action in PORTAL
    assert "async function chatWorkspaceMutation(" in INTEGRATION
    assert "idempotency_key: submission.key" in INTEGRATION
    assert "await hydrateChatWorkspace();" in INTEGRATION
    assert "await hydrateChatThread(threadId);" in INTEGRATION
    assert "chatWorkspaceBoundaryIsSafe(result.data)" in INTEGRATION
    for attr in (
        "__chatThreadId",
        "__chatThreadRevision",
        "__chatThreadVersion",
        "__chatContextId",
        "__chatContextRevision",
        "__chatTurnId",
        "__chatTurnRevision",
        "__chatWorkspaceOffset",
    ):
        assert attr in PORTAL


def test_chat_run_is_a_server_confirmed_guarded_receipt_not_fake_ai() -> None:
    """Chat Run may persist a user message, never browser-synthesized AI output.

    The execution feature flag is deliberately only a UI label.  Whether it
    is true or false, the signed server contract currently returns a guarded
    receipt with no provider, assistant, Bot, ledger, payment, job, file,
    stream, or delivery behavior.
    """
    helpers = _chat_helpers()
    for helper in (
        "chatRunPayload",
        "chatExecutionBoundaryIsSafe",
        "chatRunIsSafe",
        "chatRunSubmissionReceipt",
    ):
        assert f"function {helper}" in helpers
    # Hydration lives with the signed-path orchestration below the individual
    # workspace payload helpers.  Keep the assertion global rather than
    # accidentally cutting it out at the next module's constants.
    for helper in (
        "chatExecutionRequestIsCurrent",
        "hydrateChatExecution",
        "emptyChatRunListing",
    ):
        assert f"function {helper}" in INTEGRATION
    for boundary_flag in (
        'boundary.mode === "web_native_chat_run"',
        "boundary.run_submission_available === \"boolean\"",
        "boundary.provider_execution_available === false",
        "boundary.assistant_reply_available === false",
        "boundary.cancel_available === false",
        "boundary.provider_called === false",
        "boundary.bot_called === false",
        "boundary.wallet_mutated === false",
        "boundary.payment_started === false",
        "boundary.job_created === false",
        "boundary.output_created === false",
        "boundary.stream_available === false",
        'boundary.output_delivery === "guarded"',
    ):
        assert boundary_flag in helpers

    assert '"chat-run-submit": Boolean(account && me.csrf_token && chatWorkspaceEnabled)' in INTEGRATION
    assert '"chat-run-refresh": Boolean(account && chatWorkspaceEnabled)' in INTEGRATION
    assert 'path: `/chat-workspace/threads/${encodeURIComponent(threadId)}/runs`' in INTEGRATION
    assert 'action === "chat-run-submit"' in INTEGRATION
    assert 'action === "chat-run-refresh"' in INTEGRATION
    assert "idempotency_key: submission.key" in INTEGRATION
    assert "await hydrateChatThread(threadId);" in INTEGRATION
    assert "if (!chatExecutionBoundaryIsSafe({ execution })) throw" in INTEGRATION
    assert "chatExecution: {}, chatRuns: []" in INTEGRATION
    assert "let chatExecutionHydrationEpoch = 0" in INTEGRATION
    assert "++chatExecutionHydrationEpoch" in INTEGRATION

    # The UI has a confirmation composer and a receipt timeline, but no
    # cancel button: guarded runs resolve synchronously and have no worker to
    # stop.  It also must not retain the composed private message in a generic
    # browser draft after submit.
    for needle in (
        "function chatRunFields()",
        "function renderChatExecutionPanel(",
        "function renderChatRunTimeline(",
        'data-portal-action="chat-run-submit"',
        'data-portal-action="chat-run-refresh"',
        "data-portal-confirm=\"Gửi tin nhắn này thành Chat Run Web-native?",
        'action === "chat-run-submit") clearTransientFormDraft(route);',
        "chatExecutionEnabled: source.chatExecutionEnabled === true",
        "chatExecutionReadState:",
    ):
        assert needle in PORTAL
    for forbidden in (
        'data-portal-action="chat-run-cancel"',
        "action === \"chat-run-cancel\"",
        'data-chat-role="assistant"',
        "data-chat-typing",
        "portal-chat-assistant",
        "localStorage",
        "sessionStorage",
        "indexedDB",
        '"/internal/',
        '"/wallet',
        '"/payments',
        '"/payos',
        '"/bridge',
    ):
        assert forbidden not in _chat_surface()

    for selector in (
        ".portal-chat-execution",
        ".portal-chat-execution-status",
        ".portal-chat-execution-layout",
        ".portal-chat-run-composer",
        ".portal-chat-run-timeline",
        ".portal-chat-run-card",
    ):
        assert selector in CSS
    assert re.search(r"\.portal-chat-execution-layout[^{}]*\{ grid-template-columns: 1fr; \}", CSS)
    assert re.search(r"\.portal-chat-execution-status[^{}]*\{ grid-template-columns: 1fr; \}", CSS)


def test_chat_library_filter_and_pagination_keep_private_state_consistent() -> None:
    for helper in (
        "chatWorkspaceBoundaryIsSafe(threadListing)",
        "chatWorkspaceBoundaryIsSafe(eventListing)",
    ):
        assert helper in INTEGRATION
    for helper in (
        "CHAT_WORKSPACE_LIST_LIMIT",
        "function chatWorkspaceListOptions(overrides)",
        "function chatWorkspaceThreadsPath(options)",
        "function chatWorkspacePagination(data, requested)",
        "let chatWorkspaceSessionEpoch = 0",
        "let chatWorkspaceListHydrationEpoch = 0",
        "let chatWorkspaceDetailHydrationEpoch = 0",
        "function chatWorkspaceRequestIsCurrent(",
        "Máy chủ trả số lượng hội thoại không nhất quán.",
    ):
        assert helper in INTEGRATION
    for needle in (
        "function chatWorkspaceFilterFields()",
        "function renderChatWorkspacePagination(listing, enabled)",
        'data-portal-action="chat-workspace-filter"',
        'data-portal-action="chat-workspace-page"',
        "data-chat-workspace-offset",
        "data-portal-no-transient",
        'form.hasAttribute("data-portal-no-transient")',
    ):
        assert needle in PORTAL
    for selector in (
        ".portal-chat-workspace-filters",
        ".portal-chat-workspace-pagination",
    ):
        assert selector in CSS


def test_chat_hydration_fences_session_list_detail_and_current_signed_path() -> None:
    """A delayed signed response must not cross a session, route, or detail read.

    This is deliberately a static contract: the portal hydration helpers are
    private client code and are not exercised through a browser/provider test.
    It pins the three independent invalidation channels needed to keep a prior
    account's thread title, context, turn, or listing filter out of a new view.
    """
    for name in (
        "chatWorkspaceSessionEpoch",
        "chatWorkspaceListHydrationEpoch",
        "chatWorkspaceDetailHydrationEpoch",
    ):
        assert re.search(r"(?:\+\+|\+=\s*1)" + re.escape(name), INTEGRATION), name
    assert INTEGRATION.count("chatWorkspaceRequestIsCurrent(") >= 3
    assert "const sessionEpoch = chatWorkspaceSessionEpoch;" in INTEGRATION
    assert "const requestEpoch = ++chatWorkspaceListHydrationEpoch;" in INTEGRATION
    assert "const requestEpoch = ++chatWorkspaceDetailHydrationEpoch;" in INTEGRATION
    assert "if (!chatWorkspaceRequestIsCurrent(" in INTEGRATION
    assert "currentPortalPath()" in INTEGRATION

    # Presentation normalization must retain the signed list projection. If it
    # drops this field, a correct API response is silently rendered as page 0
    # and a refresh can reuse an unsafe/default filter instead.
    start = PORTAL.index("// AI Chat Workspace is owner-scoped.")
    end = PORTAL.index("// Analytics Workspace is a manual-only", start)
    normalizer = PORTAL[start:end]
    assert "chatWorkspaceListing:" in normalizer
    assert "source.chatWorkspaceListing" in normalizer


def test_chat_private_cache_and_responsive_ui_contract() -> None:
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-";' in SERVICE_WORKER
    assert "const BUILD_ID = workerBuildId();" in SERVICE_WORKER
    assert "const CACHE_NAME = `${CACHE_PREFIX}${BUILD_ID}`;" in SERVICE_WORKER
    assert ".filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)" in SERVICE_WORKER
    assert "api/v1/chat-workspace" in SERVICE_WORKER
    assert '"/chat"' in SERVICE_WORKER
    assert "private `/chat/*` routes" in SERVICE_WORKER
    assert "api/v1/chat-workspace" not in shell
    assert '"/chat"' not in shell
    for selector in (
        ".portal-chat-workspace-intro",
        ".portal-chat-workspace-grid",
        ".portal-chat-thread-card",
        ".portal-chat-workspace-guard-list",
        ".portal-chat-context-grid",
        ".portal-chat-turn-list",
        ".portal-chat-workspace-history",
    ):
        assert selector in CSS
    # The execution panel participates in the same mobile breakpoint.  Match
    # the responsive rule semantically so adding another chat surface to the
    # shared selector cannot silently remove this requirement.
    assert re.search(
        r"\.portal-chat-workspace-intro[^{}]*\.portal-chat-workspace-history[^{}]*\.portal-chat-execution-layout\s*\{\s*grid-template-columns:\s*1fr;\s*\}",
        CSS,
    )
    assert re.search(
        r"\.portal-chat-workspace-grid[^{}]*\.portal-chat-context-grid\s*\{\s*grid-template-columns:\s*1fr;\s*\}",
        CSS,
    )


def test_chat_composer_fields_keep_unique_accessible_ids() -> None:
    # The thread editor, context composer and turn composer can appear on one
    # screen. Their field labels must not cross-bind through duplicate IDs.
    for needle in (
        "function renderFields(fields, enabled, context, fieldValues, idNamespace)",
        'renderFields(chatThreadFields(context), canUpdate, context, chatThreadValues(thread), "chat-thread-editor-" + String(thread.id))',
        'renderFields(chatContextFields(), canContextCreate, context, {}, "chat-context-create-" + String(thread.id))',
        'renderFields(chatTurnFields(), canTurnCreate, context, {}, "chat-turn-create-" + String(thread.id))',
        "function renderChatContextKindOptions(value)",
    ):
        assert needle in PORTAL


def test_chat_backend_has_no_legacy_engine_or_payment_import() -> None:
    for forbidden in (
        "import ai_assistant",
        "from ai_assistant",
        "import google.generativeai",
        "from google import generativeai",
        "import copyfast_bridge",
        "from copyfast_bridge",
        "import wallet",
        "from wallet",
        "import PayOS",
        "from PayOS",
    ):
        assert forbidden not in WORKSPACE
