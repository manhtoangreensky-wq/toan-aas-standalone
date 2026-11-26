"""Check new note presentation without reading/writing any stored customer note."""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "tests/fixtures/image-composer-native-text-results.json").read_bytes())["rows"]
COPY = json.loads((ROOT / "tests/fixtures/image-composer-native-note-copy.json").read_bytes())["rows"]


@pytest.mark.parametrize("index", [0, 1, 2, 3])
@pytest.mark.parametrize("row", DATA, ids=lambda row: "_".join(row["source"][key] for key in ("language", "goal_code", "style_preset")))
def test_new_note_uses_selected_language_and_preserves_descriptions_and_identity(row, index, tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "unused-native-note.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "public-unit-only-composer-note-secret")
    studio = importlib.import_module("copyfast_image_studio")

    def forbidden(*args, **kwargs):
        raise AssertionError("Formatting a note must not touch storage")

    monkeypatch.setattr(studio, "transaction", forbidden)
    monkeypatch.setattr(studio, "read_transaction", forbidden)
    composer = row["result"]["composer"]
    old = json.loads(json.dumps(composer))
    labels = {item["key"]: item[row["source"]["language"]] for item in COPY}
    title, content, tags = studio._image_prompt_composer_memory_note(composer, selected_variant_index=index)
    assert composer == old
    assert title == labels["title"]
    assert content.startswith(labels["summary"])
    for key in ("selectionHeading", "short", "detailed", "avoid", "variants", "review"):
        assert "## " + labels[key] in content
    assert labels["stylePreset"] + ": " + labels["preset." + {
        "auto": "auto", "suggestion_1": "first", "suggestion_2": "second",
        "suggestion_3": "third", "custom": "custom",
    }[composer["style_preset"]]] in content
    assert labels["language"] + ": " + labels["language." + composer["language"]] in content
    selected = composer["detailed_prompt"] if index == 0 else composer["variants"][index - 1]
    assert selected in content
    for value in [composer[key] for key in ("title", "subject", "goal_label", "style", "short_prompt", "detailed_prompt", "negative_prompt")] + composer["variants"] + composer["review_before_use"]:
        assert value in content
    for ordinal in (1, 2, 3):
        assert "### " + labels["variant"].replace("{number}", str(ordinal)) in content
    assert "selected_variant_index:" not in content
    assert "Preset phong cách:" not in content
    assert "Ghi chú này không tạo ảnh, output, job" not in content
    assert tags == ["image-prompt-composer", f"image-goal-{composer['goal_code']}", f"image-prompt-variant-{index}"]


@pytest.mark.parametrize("index", [-1, 4, 0.5, "2", True, None])
def test_new_note_keeps_invalid_selection_rejection(index, tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "unused-native-note-invalid.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "public-unit-only-composer-note-secret")
    studio = importlib.import_module("copyfast_image_studio")
    with pytest.raises(studio.HTTPException) as error:
        studio._image_prompt_composer_memory_note(DATA[0]["result"]["composer"], selected_variant_index=index)
    assert error.value.status_code == 422
