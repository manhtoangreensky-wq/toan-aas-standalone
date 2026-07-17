"""Static contracts for the signed, Web-native Memory Center UI."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_memory_pages_are_real_web_workspace_surfaces_not_bot_companion_cards() -> None:
    assert 'customerPage("/notes", "Memory Center"' in PORTAL
    assert 'customerPage("/reminders", "Nhắc việc"' in PORTAL
    assert 'type: "memory-center", layout: "memory-notes"' in PORTAL
    assert 'type: "memory-center", layout: "memory-reminders"' in PORTAL
    assert "function renderMemoryNotes(page, context)" in PORTAL
    assert "function renderMemoryReminders(page, context)" in PORTAL
    assert 'case "memory-notes": return renderMemoryNotes(page, context);' in PORTAL
    assert 'case "memory-reminders": return renderMemoryReminders(page, context);' in PORTAL
    assert 'botCompanionPage("/notes"' not in PORTAL
    assert 'botCompanionPage("/reminders"' not in PORTAL


def test_memory_note_search_uses_owner_scoped_api_without_url_or_browser_persistence() -> None:
    assert "function memoryNoteFilterState(context)" in PORTAL
    assert "function memoryNoteFilterFields()" in PORTAL
    assert "function memoryNoteListing(context)" in PORTAL
    assert "function renderMemoryNotePagination(listing)" in PORTAL
    assert 'data-portal-action="memory-note-filter"' in PORTAL
    assert 'data-portal-action="memory-note-filter-clear"' in PORTAL
    assert '"memory-note-page"' in PORTAL
    assert 'data-memory-note-offset' in PORTAL
    assert 'data-portal-no-transient data-portal-action="memory-note-filter"' in PORTAL
    assert "memoryNoteFilter:" in PORTAL
    assert "Array.isArray(option) ? option[0]" in PORTAL
    assert "function memoryNoteFilterPayload(value)" in INTEGRATION
    assert "function memoryNoteListPath(filter, offset)" in INTEGRATION
    assert "memoryNoteListingProjection(filter, offset, source, returned)" in INTEGRATION
    assert "api(notePath)" in INTEGRATION
    assert 'api("/memory/events?limit=50").catch(() => null)' in INTEGRATION
    assert "function memoryEventsProjection" in INTEGRATION
    assert "memoryEventsReadState: eventProjection.readState" in INTEGRATION
    assert "action === \"memory-note-filter\"" in INTEGRATION
    assert "action === \"memory-note-filter-clear\"" in INTEGRATION
    assert "action === \"memory-note-page\"" in INTEGRATION
    assert 'action !== "memory-note-filter"' in PORTAL


def test_memory_reminder_listing_is_paged_transient_and_preserves_existing_links_explicitly() -> None:
    assert "function memoryReminderFilterState(context)" in PORTAL
    assert "function memoryReminderListing(context)" in PORTAL
    assert "function renderMemoryReminderPagination(listing)" in PORTAL
    assert 'data-portal-action="memory-reminder-filter"' in PORTAL
    assert 'data-portal-action="memory-reminder-filter-clear"' in PORTAL
    assert '"memory-reminder-page"' in PORTAL
    assert 'data-memory-reminder-offset' in PORTAL
    assert "retainedCurrentLink" in PORTAL
    assert "data-portal-no-transient" in PORTAL
    assert "function memoryReminderFilterPayload(value)" in INTEGRATION
    assert "function memoryReminderListPath(filter, offset)" in INTEGRATION
    assert "memoryReminderListingProjection(filter, offset, source, returned)" in INTEGRATION
    assert "action === \"memory-reminder-filter\"" in INTEGRATION
    assert "action === \"memory-reminder-page\"" in INTEGRATION
    assert 'startsWith("memory-")' in PORTAL
    assert "memoryEventsReadState:" in PORTAL
    renderer_start = PORTAL.index("function renderMemoryReminders(page, context)")
    renderer_end = PORTAL.index("// Prompt Library", renderer_start)
    renderer = PORTAL[renderer_start:renderer_end]
    assert "Hoạt động Memory đang tạm chưa xác minh" in renderer
    assert "coi feed là trống" in renderer


def test_memory_list_and_note_detail_hydrators_reject_stale_race_results() -> None:
    """A slow previous page/read must not overwrite the current private view."""
    list_start = INTEGRATION.index("async function hydrateMemoryCenter(")
    detail_start = INTEGRATION.index("async function hydrateMemoryNote(")
    next_hydrator = INTEGRATION.index("async function hydratePromptLibrary(")
    list_hydrator = INTEGRATION[list_start:detail_start]
    detail_hydrator = INTEGRATION[detail_start:next_hydrator]

    # The two requests intentionally use separate ordering domains: paging a
    # note library must invalidate an in-flight note body, but a note open
    # must not cancel an independent reminder/list refresh.
    assert "let memorySessionEpoch = 0;" in INTEGRATION
    assert "++memorySessionEpoch;" in INTEGRATION
    assert "let memoryListHydrationEpoch = 0;" in INTEGRATION
    assert "let memoryNoteDetailHydrationEpoch = 0;" in INTEGRATION
    assert "const requestEpoch = ++memoryListHydrationEpoch;" in list_hydrator
    assert "const sessionEpoch = memorySessionEpoch;" in list_hydrator
    assert "const requestEpoch = ++memoryNoteDetailHydrationEpoch;" in detail_hydrator
    assert "const sessionEpoch = memorySessionEpoch;" in detail_hydrator
    helper = INTEGRATION[INTEGRATION.index("function memoryRequestIsCurrent"):INTEGRATION.index("function memoryTagsFromInput")]
    for requirement in (
        "sessionEpoch === memorySessionEpoch",
        "currentPortalPath() === expectedPath",
        '["/notes", "/reminders"].includes(expectedPath)',
        "base().memoryCenterEnabled === true",
        "base().session && base().session.authenticated === true",
    ):
        assert requirement in helper

    # Filter/page navigation explicitly retires the prior detail request at
    # the same time it clears the old body. Without this increment, a late
    # /memory/notes/{id} response could repopulate a detail from another page.
    assert "const explicitListChange = noteFilterValue !== undefined || noteOffsetValue !== undefined" in list_hydrator
    assert "|| reminderFilterValue !== undefined || reminderOffsetValue !== undefined;" in list_hydrator
    selection_context = "if (explicitListChange) {"
    assert selection_context in list_hydrator
    invalidation = list_hydrator[list_hydrator.index(selection_context):]
    assert "++memoryNoteDetailHydrationEpoch;" in invalidation
    assert "merge({ memoryNoteDetail: {} });" in invalidation
    assert invalidation.index("++memoryNoteDetailHydrationEpoch;") < invalidation.index("merge({ memoryNoteDetail: {} });")

    # Both hydration paths must ignore superseded success *and* failure
    # completions before they can merge a stale ready/guarded projection.
    list_success, list_failure = list_hydrator.split("catch (", 1)
    list_guard = "if (!memoryRequestIsCurrent(requestEpoch, memoryListHydrationEpoch, sessionEpoch, path)) return { stale: true };"
    assert list_guard in list_success
    assert list_guard in list_failure
    assert list_success.rindex(list_guard) < list_success.rindex("merge({")
    assert "merge(" in list_failure
    assert list_failure.index(list_guard) < list_failure.index("merge(")

    detail_success, detail_failure = detail_hydrator.split("catch (", 1)
    detail_guard = "if (!memoryRequestIsCurrent(requestEpoch, memoryNoteDetailHydrationEpoch, sessionEpoch, expectedPath)) return { stale: true };"
    assert detail_guard in detail_success
    assert detail_guard in detail_failure
    assert detail_success.rindex(detail_guard) < detail_success.rindex("merge({")
    assert detail_failure.index(detail_guard) < detail_failure.index("merge({")
    assert "merge({ memoryNoteDetail: {} });" in detail_failure


def test_memory_actions_remain_separate_from_canonical_bridge_payment_and_pwa_cache() -> None:
    action_start = INTEGRATION.index('if (action === "memory-note-filter"')
    action_end = INTEGRATION.index('if (action === "asset-vault-upload")')
    actions = INTEGRATION[action_start:action_end].lower()
    assert "bridgeavailable" not in actions
    assert "payment" not in actions
    assert "payos" not in actions
    assert "wallet" not in actions
    assert "telegram_send" not in actions
    assert "/api/v1/memory" not in SERVICE_WORKER
    assert '"/notes"' not in SERVICE_WORKER
    assert ".portal-memory-filter" in CSS
    assert ".portal-memory-note-list" in CSS
    assert ".portal-memory-reminder-grid" in CSS
