"""Portal contract for the existing owner-scoped Memory category filter."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")


def test_memory_category_filter_is_transient_and_sent_to_the_owner_scoped_api_only() -> None:
    assert '{ name: "category", label: "Danh mục", placeholder: "Ví dụ: Marketing", maxLength: 80 }' in PORTAL
    assert "memoryNoteFilter" in PORTAL

    start = INTEGRATION.index("function memoryNoteFilterPayload(value)")
    end = INTEGRATION.index("function memoryTagsFromInput", start)
    fragment = INTEGRATION[start:end]
    assert 'const category = String(source.category || "").replace(/\\s+/g, " ").trim();' in fragment
    assert "return { q, priority, category, state };" in fragment
    assert 'if (filter.category) query.set("category", filter.category);' in fragment
    assert "localStorage" not in fragment
    assert "CORE_BRIDGE" not in fragment
