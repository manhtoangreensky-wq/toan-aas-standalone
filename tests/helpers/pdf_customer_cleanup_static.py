"""Exact test-only inverse for the unchanged historical Document safety assertions."""
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads((ROOT / "tests/fixtures/pdf-customer-cleanup-reviewed.json").read_text(encoding="utf-8"))
OWNERS = ("renderPdfSplit", "renderPdfMerge", "renderPdfOptimize")


def historical_portal_source(source: str) -> str:
    """Restore only reviewed cleanup fragments; retain every other byte."""
    source = runpy.run_path(str(ROOT / "tests/helpers/document_convert_historical_static.py"))["historical_customer_portal"](source)
    if "docPdfReadyUi" not in source and 'imageOperationText("reference.aria", "Trang tệp")' not in source:
        return source
    for index in range(len(FIXTURE["changes"]) - 1, -1, -1):
        edit = FIXTURE["changes"][index]
        if edit["file"] != "static/portal/portal.js":
            continue
        assert edit["count"] == 1
        if index < 6 or index == 8:
            owner = OWNERS[index // 2] if index < 6 else "renderPdfOptimize"
            anchor = "  function " + owner + "("
            assert source.count(anchor) == 1, "Unreviewed PDF cleanup owner"
            start = source.index(anchor)
            end = source.index("\n  function ", start + len(anchor))
            part = source[start:end]
            assert part.count(edit["new"]) == 1, "Unreviewed PDF cleanup scoped chunk"
            source = source[:start] + part.replace(edit["new"], edit["old"], 1) + source[end:]
        else:
            assert source.count(edit["new"]) == 1, "Unreviewed PDF cleanup global chunk"
            source = source.replace(edit["new"], edit["old"], 1)
    assert "docPdfReadyUi" not in source, "Unreviewed PDF cleanup residual"
    return source
