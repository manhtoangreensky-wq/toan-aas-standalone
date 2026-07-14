"""Focused portal contracts for the Web-native AI Chat Workspace.

The UI must remain a private authoring application rather than reintroducing
the old generic `/chat` Core Bridge estimate surface or pretending to run AI.
"""

from pathlib import Path


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
    assert "Lưu hội thoại, không chạy AI" in surface
    assert "không phải model" in surface
    assert "assistant role" in surface
    for forbidden in (
        "fetch(",
        "api(",
        "localStorage",
        'data-portal-action="chat-workspace-execute"',
        'data-portal-action="chat-workspace-estimate"',
        'data-portal-action="chat-workspace-confirm"',
        'data-portal-action="chat-workspace-download"',
        "assistant_reply",
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
        "let chatWorkspaceHydrationEpoch = 0",
        "if (requestEpoch !== chatWorkspaceHydrationEpoch) return { stale: true }",
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


def test_chat_private_cache_and_responsive_ui_contract() -> None:
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert 'const CACHE_NAME = "toan-aas-portal-shell-v14"' in SERVICE_WORKER
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
        ".portal-chat-workspace-intro, .portal-chat-thread-summary, .portal-chat-workspace-layout, .portal-chat-workspace-detail-grid, .portal-chat-workspace-history { grid-template-columns: 1fr; }",
        ".portal-chat-workspace-grid, .portal-chat-context-grid { grid-template-columns: 1fr; }",
    ):
        assert selector in CSS


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
