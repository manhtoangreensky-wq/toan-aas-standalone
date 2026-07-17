"""Static contracts for the Support Desk private evidence picker."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_support_evidence_picker_reuses_asset_vault_without_raw_upload_or_pwa_cache() -> None:
    start = PORTAL.index("function renderSupportEvidence")
    end = PORTAL.index("function pagePathForSupportCase", start)
    picker = PORTAL[start:end]
    assert 'data-portal-action="support-case-attachment"' in picker
    assert 'href="/asset-vault"' in picker
    assert 'name="asset_id"' in picker
    assert 'name="customer_redaction_confirmed"' in picker
    assert 'type="file"' not in picker
    assert "Không upload tệp tại Support Desk" in picker

    assert "function supportEvidenceAssetCandidates" in INTEGRATION
    assert 'api(`/asset-vault?state=active&limit=${SUPPORT_ATTACHMENT_ASSET_LIST_LIMIT}`)' in INTEGRATION
    assert 'if (action === "support-case-attachment")' in INTEGRATION
    assert 'api(`/support/cases/${encodeURIComponent(caseId)}/attachments`' in INTEGRATION
    assert "customer_redaction_confirmed: true" in INTEGRATION

    assert "/api/v1/support" not in SERVICE_WORKER
    assert '"/support"' not in SERVICE_WORKER
    assert '"/tickets"' not in SERVICE_WORKER
