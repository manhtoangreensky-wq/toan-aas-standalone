"""Browser-side privacy contract for Document Workspace event metadata."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).parents[1]
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")


def _workspace_helpers() -> str:
    start = INTEGRATION.index("const DOCUMENT_WORKSPACE_TYPES")
    return INTEGRATION[start:INTEGRATION.index("const SUBTITLE_STUDIO_FORMATS", start)]


def test_document_workspace_event_projection_is_closed_and_content_free() -> None:
    helpers = _workspace_helpers()
    for marker in (
        "const DOCUMENT_WORKSPACE_EVENT_ACTIONS",
        "const DOCUMENT_WORKSPACE_EVENT_ENTITY_TYPES",
        "const DOCUMENT_WORKSPACE_EVENT_FIELDS",
        "function documentWorkspaceTimestampIsSafe(value)",
        "function documentWorkspaceEventIsSafe(value)",
        "function documentWorkspaceEventsProjection(value)",
    ):
        assert marker in helpers
    assert "const events = documentWorkspaceEventsProjection(eventData);" in INTEGRATION
    assert "|| !policy || !events)" in INTEGRATION

    event_start = helpers.index("const DOCUMENT_WORKSPACE_TYPES")
    event_end = helpers.index("function documentWorkspaceIdFromPath", event_start)
    event_helpers = helpers[event_start:event_end]
    boundary_start = helpers.index("function documentWorkspaceBoundaryIsSafe")
    boundary_end = helpers.index("function documentWorkspaceHandoffText", boundary_start)
    boundary_helper = helpers[boundary_start:boundary_end]

    workspace_id = "12345678-1234-4234-8234-1234567890ab"
    plan_id = "87654321-4321-4234-8234-ba0987654321"
    created_at = "2026-08-14T10:30:00+00:00"
    runner = """
const vm = require("vm");
const helpers = %s;
const boundaryHelper = %s;
const workspaceId = %s;
const planId = %s;
const createdAt = %s;
const sandbox = {
  validProjectId: (value) => /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || "").trim()),
  validMemoryRevision: (value) => {
    const parsed = Number(value);
    return Number.isInteger(parsed) && parsed >= 1 && parsed <= 1000000 ? parsed : 0;
  },
};
vm.runInNewContext(helpers + "\\n" + boundaryHelper, sandbox);
const boundary = {
  execution: "authoring_only", provider_called: false, ocr_called: false,
  translation_called: false, output_created: false, job_created: false,
  payment_started: false, wallet_mutated: false, payment_processed: false,
  browser_file_upload: false, browser_media_url: false, preview_available: false,
  output_delivery: "guarded"
};
const workspaceEvent = {
  action: "workspace_created", entity_type: "workspace", workspace_id: workspaceId,
  plan_id: null, revision: 1, created_at: createdAt
};
const planEvent = {
  action: "plan_updated", entity_type: "plan", workspace_id: workspaceId,
  plan_id: planId, revision: 2, created_at: createdAt
};
const unknownAction = { ...workspaceEvent, action: "unexpected_event" };
const extraField = { ...workspaceEvent, source_text: "MUST_NOT_RENDER" };
const mismatchedPlan = { ...workspaceEvent, entity_type: "workspace", plan_id: planId };
const malformedTime = { ...workspaceEvent, created_at: "not-a-time" };
const unsafeBoundary = { ...boundary, provider_called: true };
process.stdout.write(JSON.stringify({
  valid: sandbox.documentWorkspaceEventsProjection({ ...boundary, items: [workspaceEvent, planEvent] }),
  unknownAction: sandbox.documentWorkspaceEventsProjection({ ...boundary, items: [unknownAction] }),
  extraField: sandbox.documentWorkspaceEventsProjection({ ...boundary, items: [extraField] }),
  mismatchedPlan: sandbox.documentWorkspaceEventsProjection({ ...boundary, items: [mismatchedPlan] }),
  malformedTime: sandbox.documentWorkspaceEventsProjection({ ...boundary, items: [malformedTime] }),
  unsafeBoundary: sandbox.documentWorkspaceEventsProjection({ ...unsafeBoundary, items: [workspaceEvent] })
}));
""" % (json.dumps(event_helpers), json.dumps(boundary_helper), json.dumps(workspace_id), json.dumps(plan_id), json.dumps(created_at))
    result = subprocess.run(["node", "-e", runner], check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    assert payload["valid"] == [
        {"action": "workspace_created", "revision": 1, "created_at": created_at},
        {"action": "plan_updated", "revision": 2, "created_at": created_at},
    ]
    assert payload["unknownAction"] is None
    assert payload["extraField"] is None
    assert payload["mismatchedPlan"] is None
    assert payload["malformedTime"] is None
    assert payload["unsafeBoundary"] is None


def test_document_workspace_activity_card_is_reused_without_identifier_rendering() -> None:
    assert "function renderDocumentWorkspaceActivity(events)" in PORTAL
    start = PORTAL.index("function renderDocumentWorkspaceActivity(events)")
    helper = PORTAL[start:PORTAL.index("function renderDocumentWorkspaceDetail", start)]
    runner = """
const vm = require("vm");
const helper = %s;
const sandbox = {
  renderDocumentWorkspaceEvents: (events) => "<safe-events>" + events.length + "</safe-events>"
};
vm.runInNewContext(helper, sandbox);
const markup = sandbox.renderDocumentWorkspaceActivity([{ action: "workspace_created", revision: 1, created_at: "2026-08-14T10:30:00+00:00" }]);
process.stdout.write(markup);
""" % json.dumps(helper)
    result = subprocess.run(["node", "-e", runner], check=True, capture_output=True, text=True)
    assert "Hoạt động gần đây" in result.stdout
    assert "Feed chỉ hiển thị nhãn, revision và thời điểm" in result.stdout
    assert "<safe-events>1</safe-events>" in result.stdout
    assert "workspace_id" not in result.stdout
    assert "plan_id" not in result.stdout
