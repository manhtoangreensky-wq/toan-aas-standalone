"""Exact input inverse for tests predating the Image presentation changes."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "tests/fixtures/image-studio-presentation-contract.json").read_bytes())
FAIL = "Unreviewed Image Studio presentation"
assert CONTRACT["base"] == "07a89b79c442981ecb7433b607c981740c95c774", FAIL
assert len(CONTRACT["copy"]) == 19 and len(CONTRACT["otherRecords"]) == 4, FAIL


def _line(row):
    return "    [" + ", ".join(json.dumps(value, ensure_ascii=False) for value in row) + "],"


def image_studio_presentation_historical_source(source: str, file: str) -> str:
    assert isinstance(source, str) and isinstance(file, str), FAIL
    if file == "static/portal/portal-i18n.js":
        if _line(CONTRACT["copy"][0][2]) not in source:
            return source
        for _, _, next_row in CONTRACT["copy"]:
            assert source.count(_line(next_row)) == 1, FAIL
        for _, old, next_row in CONTRACT["copy"]:
            source = source.replace(_line(next_row), _line(old), 1)
    elif file == "static/portal/portal.js":
        if "  function renderImageStudioBoundary() {" not in source or source.count("renderImageStudioBoundary()") == 3:
            return source
        assert source.count("renderImageStudioBoundary()") == 1, FAIL
        create = '</button></div></form></section></div>\n      ${imageHub ? renderImageHubNextSteps() : ""}'
        detail = '    </article>`;\n  }\n\n  // AI Chat Workspace'
        assert source.count(create) == 1 and source.count(detail) == 1, FAIL
        source = source.replace(create, create.replace("</section></div>", "</section>${renderImageStudioBoundary()}</div>"), 1)
        source = source.replace(detail, "      ${renderImageStudioBoundary()}\n" + detail, 1)
    elif file == "static/portal/portal-theme.css":
        records = [row for row in CONTRACT["otherRecords"] if row["file"] == file]
        if not any(row["new"] in source for row in records):
            return source
        for row in records:
            assert source.count(row["new"]) == 1, FAIL
        for row in records:
            source = source.replace(row["new"], row["old"], 1)
    return source
