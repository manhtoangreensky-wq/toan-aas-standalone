import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const portal = fs.readFileSync("static/portal/portal.js", "utf8");
const css = fs.readFileSync("static/portal/portal-theme.css", "utf8");
const i18n = fs.readFileSync("static/portal/portal-i18n.js", "utf8");

function section(startMarker, endMarker) {
  const start = portal.indexOf(startMarker);
  const end = portal.indexOf(endMarker, start + startMarker.length);
  assert.ok(start >= 0 && end > start, `missing source section: ${startMarker}`);
  return portal.slice(start, end);
}

function referenceProjection() {
  const source = section("function adminDataReferenceProjection", "function renderRowsTable");
  return new Function(`${source}; return adminDataReferenceProjection;`)();
}

function referenceChainProjection() {
  const source = section("function adminDataReferenceProjection", "function renderRowsTable");
  return new Function(`${source}; return adminDataReferenceChainProjection;`)();
}

test("Admin record references accept only bounded internal server-issued links", () => {
  const project = referenceProjection();
  const chain = referenceChainProjection();
  assert.deepEqual(project({
    admin_record_references: [
      { kind: "request", id: "REQ-01", label: "Yêu cầu", path: "/admin/requests/REQ-01" },
      { kind: "job", id: "JOB-01", path: "/admin/jobs/JOB-01" },
      { kind: "asset", id: "AST-01", path: "/assets/AST-01" }
    ]
  }), [
    { kind: "request", id: "REQ-01", label: "Yêu cầu", path: "/admin/requests/REQ-01" },
    { kind: "job", id: "JOB-01", label: "JOB-01", path: "/admin/jobs/JOB-01" },
    { kind: "asset", id: "AST-01", label: "AST-01", path: "/assets/AST-01" }
  ]);
  assert.deepEqual(project({ admin_record_references: [{ kind: "job", id: "JOB-01", path: "https://evil.example" }] }), [
    { kind: "job", id: "JOB-01", label: "JOB-01", path: "" }
  ]);
  assert.deepEqual(project({ admin_record_references: [
    { kind: "job", id: "JOB-01", path: "/admin/../users/JOB-01" },
    { kind: "asset", id: "AST-01", path: "/assets/%2e%2e/private/AST-01" }
  ] }), [
    { kind: "job", id: "JOB-01", label: "JOB-01", path: "" },
    { kind: "asset", id: "AST-01", label: "AST-01", path: "" }
  ]);
  assert.deepEqual(project({ admin_record_references: [{ kind: "provider", id: "PROV-01" }] }), []);
  assert.deepEqual(project({ admin_record_references: Array.from({ length: 7 }, (_, index) => ({ kind: "job", id: `JOB-${index}` })) }), []);
  assert.deepEqual(chain({ admin_record_references: [
    { kind: "audit", id: "AUD-01" },
    { kind: "asset", id: "AST-01" },
    { kind: "request", id: "REQ-01" },
    { kind: "report", id: "REP-01" },
    { kind: "job", id: "JOB-01" }
  ] }).map((reference) => reference.kind), ["request", "job", "asset", "report", "audit"]);
});

test("Admin data table and inspector expose bounded references without write actions", () => {
  const table = section("function renderRowsTable", "function dashboardActiveDrafts");
  const inspector = section("function selectAdminDataViewRow", "function syncAdminDataViewRows");
  assert.match(table, /adminDataReferenceProjection\(row\)/);
  assert.match(table, /data-admin-record-references/);
  assert.match(table, /JSON\.stringify\(references\)/);
  assert.match(inspector, /referenceTitle/);
  assert.match(inspector, /referenceChainTitle/);
  assert.match(inspector, /referenceKind\./);
  assert.match(inspector, /portal-admin-data-reference-link/);
  assert.match(inspector, /portal-admin-data-reference-chain/);
  assert.doesNotMatch(inspector, /fetch\(|XMLHttpRequest/);
  for (const key of [
    "referenceTitle",
    "referenceKind.request",
    "referenceKind.job",
    "referenceKind.asset",
    "referenceKind.report",
    "referenceKind.audit",
    "referenceChainTitle"
  ]) {
    assert.equal((i18n.match(new RegExp(`\\"adminDataView\\.${key}\\"`, "g")) || []).length, 3, `${key} must exist in VI/EN/ZH`);
  }
  assert.match(css, /\.portal-admin-data-reference-list/);
  assert.match(css, /\.portal-admin-data-reference-link/);
  assert.match(css, /\.portal-admin-data-reference-chain/);
});
