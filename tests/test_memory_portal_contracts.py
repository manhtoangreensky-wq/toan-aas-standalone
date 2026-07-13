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
    assert 'data-portal-action="memory-note-filter"' in PORTAL
    assert 'data-portal-action="memory-note-filter-clear"' in PORTAL
    assert "memoryNoteFilter:" in PORTAL
    assert "Array.isArray(option) ? option[0]" in PORTAL
    assert "function memoryNoteFilterPayload(value)" in INTEGRATION
    assert "function memoryNoteListPath(filter)" in INTEGRATION
    assert "api(memoryNoteListPath(filter))" in INTEGRATION
    assert "action === \"memory-note-filter\"" in INTEGRATION
    assert "action === \"memory-note-filter-clear\"" in INTEGRATION
    assert 'action !== "memory-note-filter"' in PORTAL


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
