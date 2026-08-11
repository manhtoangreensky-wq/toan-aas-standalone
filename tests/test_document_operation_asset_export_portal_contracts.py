"""Static portal contracts for Document Operation → Asset Vault export."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")

ACTION = "document-operation-export-to-asset-vault"
ROUTE_SUFFIX = "/export-to-asset-vault"


def _between(source: str, start_marker: str, end_pattern: str) -> str:
    assert start_marker in source
    start = source.index(start_marker)
    following = re.search(end_pattern, source[start + len(start_marker):])
    end = len(source) if following is None else start + len(start_marker) + following.start()
    return source[start:end]


def _action_source() -> str:
    return _between(INTEGRATION, f'if (action === "{ACTION}")', r"\n\s*if \(action === ")


def _named_action_source(action: str) -> str:
    return _between(INTEGRATION, f'if (action === "{action}")', r"\n\s*if \(action === ")


def test_portal_publishes_the_effective_document_export_capability_through_bootstrap() -> None:
    assert "const documentOperationExportEnabled" in INTEGRATION
    assert '"document-operation-export-to-asset-vault": Boolean(account && me.csrf_token && assetVaultEnabled && documentOperationsEnabled && documentOperationExportEnabled)' in INTEGRATION
    bootstrap = _between(PORTAL, "function normalizeBootstrap", "function getBootstrap")
    assert "documentOperationExportEnabled: source.documentOperationExportEnabled === true" in bootstrap


def test_document_cards_offer_a_confirmed_quiet_export_only_for_verified_pdf_docx_or_txt_outputs() -> None:
    cards = _between(PORTAL, "function renderDocumentOperationCards", "function renderDocumentHub")
    assert f'data-portal-action="{ACTION}"' in cards
    assert "data-portal-confirm=" in cards
    assert "portal-button--quiet" in cards
    assert 'data-document-operation-id="${safeText(String(item.id))}"' in cards
    assert 'status === "completed"' in cards
    assert "item.download_ready === true" in cards
    for allowed_kind in ("pdf_split", "pdf_merge", "pdf_optimize", "image_to_pdf", "pdf_to_word_text", "image_ocr", "pdf_ocr", "pdf_ocr_word"):
        assert f'"{allowed_kind}"' in cards
    assert '"pdf_to_images"' not in _between(cards, "const canExport", "const start")


def test_completed_document_card_renders_the_export_control_with_its_active_context() -> None:
    """Execute the card helper so an undeclared `context` cannot hide in static checks."""

    helper = _between(PORTAL, "function renderDocumentOperationCards", "function renderDocumentHub")
    operation_id = "12345678-1234-4234-8234-1234567890ab"
    context = {
        "path": "/documents/split",
        "capabilities": {ACTION: True},
    }
    runner = """
const vm = require("vm");
const helper = %s;
const operation = %s;
const renderContext = %s;
const sandbox = {
  renderEmpty: () => "",
  documentOperationState: (item) => String(item.state || "guarded"),
  documentOperationDownloadPath: (item) => item.download_ready === true ? "/private-download" : "",
  imageOcrLanguageLabel: () => "auto",
  vaultBytes: (value) => String(value),
  safeText: (value) => String(value),
  badge: (value) => `<span>${value}</span>`,
};
vm.runInNewContext(helper, sandbox);
const markup = sandbox.renderDocumentOperationCards([operation], renderContext, "", "");
process.stdout.write(JSON.stringify({ markup }));
""" % (json.dumps(helper), json.dumps({
        "id": operation_id,
        "kind": "pdf_split",
        "state": "completed",
        "download_ready": True,
        "original_filename": "toan-aas-pdf-pages-1-2.pdf",
        "selected_start_page": 1,
        "selected_end_page": 2,
        "source_page_count": 2,
        "output_page_count": 2,
        "byte_size": 512,
    }), json.dumps(context))
    result = subprocess.run(["node", "-e", runner], check=True, capture_output=True, text=True)
    markup = json.loads(result.stdout)["markup"]
    assert f'data-portal-action="{ACTION}"' in markup
    assert f'data-document-operation-id="{operation_id}"' in markup
    assert 'data-portal-route="/documents/split"' in markup


def test_document_operation_routes_pass_their_live_context_to_history_cards() -> None:
    """Every workspace that can render the action keeps its route/capability context."""

    callers = (
        "renderDocumentHub",
        "renderPdfSplit",
        "renderPdfMerge",
        "renderPdfOptimize",
        "renderPdfToImages",
        "renderPdfToWord",
        "renderImageOcr",
        "renderPdfOcr",
        "renderPdfOcrToWord",
        "renderImageToPdf",
    )
    for caller in callers:
        source = _between(PORTAL, f"function {caller}", r"\n  function ")
        assert re.search(r"renderDocumentOperationCards\(operations,\s*context(?:,|\))", source), caller


def test_document_export_action_keeps_the_browser_to_one_opaque_same_origin_post() -> None:
    action = _action_source()
    assert "validDocumentOperationId(operationId)" in action
    assert "encodeURIComponent(operationId)" in action
    assert ROUTE_SUFFIX in action
    assert "api(" in action
    assert '"Idempotency-Key": submission.key' in action
    assert "acquireSubmission" in action
    assert "releaseSubmission(submission)" in action
    assert "discardSubmission(scope, submission)" in action
    assert "hydrateDocumentOperations" in action
    assert "hydrateAssetVault" in action
    assert "acknowledged = true" in action
    assert 'assetState === "unavailable"' in action
    for forbidden in (
        "fetch(", "blob", "arraybuffer", "filereader", "formdata", "provider", "bridge",
        "telegram", "bot", "wallet", "payment", "payos", "storage_key", "sha256",
        "source_asset_id", "file_path", "filename",
    ):
        assert forbidden not in action.lower()


def test_document_export_action_extracts_only_the_card_operation_uuid() -> None:
    extraction = _between(PORTAL, f'if (action === "{ACTION}")', r"\n\s*if \(")
    assert '__documentOperationId: source.getAttribute("data-document-operation-id") || ""' in extraction
    for forbidden in ("path", "blob", "filename", "source_asset_id", "storage_key"):
        assert forbidden not in extraction.lower()


def test_asset_export_nonterminal_receipts_are_handled_without_generic_error_flow() -> None:
    """`api()` throws 200/ok:false receipts, so both private export actions must normalize them."""

    helper = _between(INTEGRATION, "function assetExportNonterminalEnvelope", "function merge")
    runner = """
const vm = require("vm");
const helper = %s;
const sandbox = {};
vm.runInNewContext(helper, sandbox);
const processing = sandbox.assetExportNonterminalEnvelope({
  status: 200,
  payload: { ok: false, status: "processing", message: "Đang xác minh" },
});
const guarded = sandbox.assetExportNonterminalEnvelope({
  status: 200,
  payload: { ok: false, status: "guarded", message: "Bị chặn an toàn" },
});
const queued = sandbox.assetExportNonterminalEnvelope({
  status: 200,
  payload: { ok: false, status: "queued", message: "Đang xếp hàng" },
});
const rejected = sandbox.assetExportNonterminalEnvelope({
  status: 403,
  payload: { ok: false, status: "guarded", message: "CSRF không hợp lệ" },
});
const malformed = sandbox.assetExportNonterminalEnvelope({
  status: 200,
  payload: { ok: false, status: "completed", message: "Không có receipt hợp lệ" },
});
process.stdout.write(JSON.stringify({ processing, guarded, queued, rejected, malformed }));
""" % json.dumps(helper)
    result = subprocess.run(["node", "-e", runner], check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    assert payload["processing"] == {"status": "processing", "message": "Đang xác minh"}
    assert payload["guarded"] == {"status": "guarded", "message": "Bị chặn an toàn"}
    assert payload["queued"] == {"status": "queued", "message": "Đang xếp hàng"}
    assert payload["rejected"] is None
    assert payload["malformed"] is None

    for action_name in (ACTION, "image-operation-export-to-asset-vault"):
        action = _named_action_source(action_name)
        assert "const nonterminal = assetExportNonterminalEnvelope(error);" in action
        assert "if (nonterminal) {" in action
        assert "await refreshPrivateState();" in action
        assert "return;" in action[action.index("if (nonterminal) {"):]
        assert "if (acknowledged) discardSubmission(scope, submission);" in action

    image_action = _named_action_source("image-operation-export-to-asset-vault")
    assert 'const responseStatus = String(result && result.status || "");' in image_action
    assert 'if (responseStatus !== "completed" || !asset' in image_action


def test_pwa_does_not_cache_private_document_export_writes_or_outputs() -> None:
    shell = _between(SERVICE_WORKER, "const SHELL =", "const SHELL_PATHS")
    assert "/api/v1/document-operations" not in shell
    assert "PRIVATE_PATH_PREFIXES" in SERVICE_WORKER
    assert "request.method !== \"GET\"" in SERVICE_WORKER
    assert "url.origin !== self.location.origin" in SERVICE_WORKER
