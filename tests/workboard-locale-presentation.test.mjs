import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const i18nSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal-i18n.js"), "utf8");
const portalSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const context = {};
vm.createContext(context);
vm.runInContext(i18nSource, context);
const messages = context.TOANAASI18n.messages;
const start = portalSource.indexOf("  // Workboard remains");
const end = portalSource.indexOf("  const CONTENT_HANDOFF_STATUS_LABELS", start);
assert.notEqual(start, -1, "Workboard source boundary exists");
assert.notEqual(end, -1, "Workboard ends before the next feature");
const source = portalSource.slice(start, end);

test("Workboard has equal VI/EN/ZH fixed chrome", () => {
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).filter((key) => key.startsWith("workboard.")).sort());
  assert.deepEqual(keysets[1], keysets[0], "Workboard VI and EN keysets must remain equal");
  assert.deepEqual(keysets[2], keysets[0], "Workboard VI and ZH keysets must remain equal");
  assert.ok(keysets[0].length >= 140, "Workboard catalogue must cover board, authoring, checklist, history and schedule chrome");
  for (const key of [
    "workboard.page.title",
    "workboard.state.backlog",
    "workboard.reference.project",
    "workboard.create.submit",
    "workboard.checklist.markDone",
    "workboard.history.restoreConfirm",
    "workboard.schedule.state.guarded",
    "workboard.detail.editorTitle"
  ]) {
    assert.ok(messages.vi[key] && messages.en[key] && messages.zh[key], "missing Workboard locale copy: " + key);
  }
});

test("Workboard routes and renderer use localized fixed copy", () => {
  for (const helperCall of [
    'workboardText("tabs.board"',
    'workboardText("library.title"',
    'workboardText("create.title"',
    'workboardText("checklist.title"',
    'workboardText("history.title"',
    'workboardText("schedule.title"',
    'workboardText("detail.editorTitle"'
  ]) {
    assert.ok(source.includes(helperCall), "Workboard must use localized helper: " + helperCall);
  }
  for (const staleFixedCopy of [
    "New work item",
    "Item editor",
    "Workflow state",
    "Version history",
    "Private planning workspace",
    "Work item library",
    "signed Web account",
    "external reference",
    "record Inbox",
    "scheduler",
    "Checklist item"
  ]) {
    assert.ok(!source.includes(staleFixedCopy), "mixed-language Workboard copy remains: " + staleFixedCopy);
  }
  for (const contract of [
    'data-portal-action="workboard-create"',
    'data-portal-action="workboard-update"',
    'data-portal-action="workboard-state"',
    'data-portal-action="workboard-checklist-update"',
    'data-portal-action="workboard-schedule-create"',
    'data-workboard-item-id=',
    'data-workboard-item-revision=',
    'workboardReferenceMarkup',
    'renderWorkboardHistoryPagination'
  ]) {
    assert.ok(source.includes(contract), "Workboard workflow contract missing: " + contract);
  }
});

test("Workboard route metadata is locale-aware", () => {
  assert.match(portalSource, /path === "\/workboard\/new"\) return workboardText\("page\.newTitle"/);
  assert.match(portalSource, /path === "\/workboard" \|\| path\.startsWith\("\/workboard\/"\)\) return workboardText\("page\.title"/);
  assert.match(portalSource, /path === "\/workboard\/new"\) return workboardText\("page\.newDescription"/);
});

test("Workboard board label and guarded recovery use reviewed locale keys", () => {
  assert.match(source, /aria-label=\"' \+ safeText\(workboardText\("board\.kicker"/);
  assert.match(source, /workboardText\("recovery\.guarded",/);
  assert.doesNotMatch(source, /workboardText\("recovery\.guardedBody",/);
  assert.ok(messages.vi["workboard.board.kicker"] && messages.en["workboard.board.kicker"] && messages.zh["workboard.board.kicker"]);
  assert.ok(messages.vi["workboard.recovery.guarded"] && messages.en["workboard.recovery.guarded"] && messages.zh["workboard.recovery.guarded"]);
});
