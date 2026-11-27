"""Native VI/EN/ZH static copy lookup for the standalone Prompt Library."""

import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

__all__ = (
    "SUPPORTED_LOCALES",
    "gallery_copy",
    "gallery_locale_text",
    "gallery_taxonomy_label",
    "localized_gallery_item",
)

SUPPORTED_LOCALES: tuple[str, ...] = ("vi", "en", "zh")
_LOCALE_SET = frozenset(SUPPORTED_LOCALES)
_EXPECTED_ROW_COUNT = 117
_DATA_FILE = Path(__file__).resolve().with_name("gallery_static_locales.json")
_TAXONOMY_KINDS = frozenset({"goal", "platform"})
_EXPECTED_FIELDS: Mapping[str, frozenset[str]] = MappingProxyType({
    "category": frozenset({"title", "title_template", "prompt_template"}),
    "industry": frozenset({"title", "product", "audience", "benefit"}),
    "goal": frozenset({"label"}),
    "platform": frozenset({"label"}),
})

_CHROME_TEXT: Mapping[str, Mapping[str, str]] = MappingProxyType({
    "description": MappingProxyType({
        "vi": "Duyệt và chọn câu lệnh phù hợp với nhu cầu của bạn.",
        "en": "Browse and choose a suitable prompt for your needs.",
        "zh": "浏览并选择适合您需求的提示词。",
    }),
    "copy_instruction": MappingProxyType({
        "vi": "Kiểm tra kỹ độ chính xác, nguồn tham khảo, quyền sử dụng và các tuyên bố trước khi xuất bản.",
        "en": "Review accuracy, sources, usage rights, and claims carefully before publishing.",
        "zh": "发布前请仔细核对准确性、来源、使用权限及相关声明。",
    }),
    "note.category": MappingProxyType({
        "vi": "Thư viện câu lệnh",
        "en": "Prompt Library",
        "zh": "提示词库",
    }),
    "note.intro": MappingProxyType({
        "vi": "Câu lệnh này được lưu từ Thư viện câu lệnh TOAN AAS.",
        "en": "This prompt was saved from the TOAN AAS Prompt Library.",
        "zh": "此提示词保存自 TOAN AAS 提示词库。",
    }),
    "note.version": MappingProxyType({
        "vi": "Phiên bản",
        "en": "Version",
        "zh": "版本",
    }),
    "note.identifier": MappingProxyType({
        "vi": "Mã mẫu",
        "en": "Sample ID",
        "zh": "示例编号",
    }),
    "note.footer": MappingProxyType({
        "vi": "Lưu ý: Kiểm tra lại độ chính xác, nguồn tham khảo, quyền sử dụng và các tuyên bố trước khi xuất bản.",
        "en": "Note: Review accuracy, sources, usage rights, and claims before publishing.",
        "zh": "注意：发布前请核对准确性、来源、使用权限及相关声明。",
    }),
})


def _require_nonempty_str(value: Any, label: str) -> str:
    """Validate that value is a non-empty, non-whitespace string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expected non-empty string for {label}")
    return value


def _require_locale(lang: str) -> str:
    """Validate that lang is an exact supported gallery locale."""
    if not isinstance(lang, str) or lang not in _LOCALE_SET:
        raise ValueError(f"Unsupported gallery locale: {lang!r}")
    return lang


def _load_locale_table(path: Path = _DATA_FILE) -> Mapping[tuple[str, str, str], Mapping[str, str]]:
    """Load and validate the frozen 117-row gallery static locale table once."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("Gallery locale payload must be a JSON object")
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) != _EXPECTED_ROW_COUNT:
        raise ValueError(f"Expected {_EXPECTED_ROW_COUNT} gallery locale rows")

    table: dict[tuple[str, str, str], Mapping[str, str]] = {}
    fields_by_group: dict[tuple[str, str], set[str]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"Gallery locale row {index} must be an object")
        kind = _require_nonempty_str(row.get("kind"), f"rows[{index}].kind")
        item_id = _require_nonempty_str(row.get("id"), f"rows[{index}].id")
        field = _require_nonempty_str(row.get("field"), f"rows[{index}].field")
        allowed_fields = _EXPECTED_FIELDS.get(kind)
        if allowed_fields is None or field not in allowed_fields:
            raise ValueError(f"Unexpected gallery locale tuple: {(kind, item_id, field)!r}")

        key = (kind, item_id, field)
        if key in table:
            raise ValueError(f"Duplicate gallery locale tuple: {key!r}")

        after = row.get("after")
        if not isinstance(after, Mapping) or set(after.keys()) != _LOCALE_SET:
            raise ValueError(f"Row {key!r} must define exact locales {SUPPORTED_LOCALES}")

        localized_values = {
            locale: _require_nonempty_str(after.get(locale), f"{key!r}.{locale}")
            for locale in SUPPORTED_LOCALES
        }
        table[key] = MappingProxyType(localized_values)
        fields_by_group.setdefault((kind, item_id), set()).add(field)

    for (kind, item_id), seen_fields in fields_by_group.items():
        if seen_fields != _EXPECTED_FIELDS[kind]:
            raise ValueError(f"Incomplete fields for {(kind, item_id)!r}")

    return MappingProxyType(table)


_LOCALE_TABLE: Mapping[tuple[str, str, str], Mapping[str, str]] = _load_locale_table()


def gallery_copy(kind: str, id: str, field: str, lang: str) -> str:
    """Return exact native gallery copy for (kind, id, field) in lang."""
    locale = _require_locale(lang)
    if not isinstance(kind, str) or not isinstance(id, str) or not isinstance(field, str):
        raise KeyError((kind, id, field))
    entry = _LOCALE_TABLE.get((kind, id, field))
    if entry is None:
        raise KeyError((kind, id, field))
    return entry[locale]


def localized_gallery_item(item: Mapping[str, Any], lang: str) -> dict[str, Any]:
    """Return a fresh localized copy of a canonical nine-key gallery item."""
    locale = _require_locale(lang)
    if not isinstance(item, Mapping):
        raise TypeError("Gallery item must be a mapping")
    category_id = item.get("category_id")
    industry_id = item.get("industry_id")
    if not isinstance(category_id, str) or not isinstance(industry_id, str):
        raise KeyError((category_id, industry_id))

    category_title = gallery_copy("category", category_id, "title", locale)
    title_template = gallery_copy("category", category_id, "title_template", locale)
    prompt_template = gallery_copy("category", category_id, "prompt_template", locale)

    industry_title = gallery_copy("industry", industry_id, "title", locale)
    variables = {
        "industry": industry_title,
        "product": gallery_copy("industry", industry_id, "product", locale),
        "audience": gallery_copy("industry", industry_id, "audience", locale),
        "benefit": gallery_copy("industry", industry_id, "benefit", locale),
    }

    localized = {
        key: (list(value) if isinstance(value, list) else value)
        for key, value in item.items()
    }
    localized["category_title"] = category_title
    localized["industry"] = industry_title
    localized["title"] = title_template.format(**variables)
    localized["prompt"] = prompt_template.format(**variables)
    return localized


def gallery_taxonomy_label(kind: str, id: str, lang: str) -> str:
    """Return finite goal or platform label, or id unchanged when unknown."""
    locale = _require_locale(lang)
    if not isinstance(id, str):
        raise TypeError("id must be a string")
    if isinstance(kind, str) and kind in _TAXONOMY_KINDS:
        entry = _LOCALE_TABLE.get((kind, id, "label"))
        if entry is not None:
            return entry[locale]
    return id


def gallery_locale_text(key: str, lang: str) -> str:
    """Return fixed native gallery UI chrome copy for key in lang."""
    locale = _require_locale(lang)
    if not isinstance(key, str):
        raise KeyError(key)
    entry = _CHROME_TEXT.get(key)
    if entry is None:
        raise KeyError(key)
    return entry[locale]
