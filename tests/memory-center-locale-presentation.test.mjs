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
const start = portalSource.indexOf("  // Memory Center mirrors");
const end = portalSource.indexOf("  // Prompt Library is intentionally", start);
assert.notEqual(start, -1, "Memory Center source boundary exists");
assert.notEqual(end, -1, "Memory Center ends before Prompt Library");
const source = portalSource.slice(start, end);

test("Memory Center has equal VI/EN/ZH fixed chrome", () => {
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).filter((key) => key.startsWith("memory.")).sort());
  assert.deepEqual(keysets[1], keysets[0], "Memory Center VI and EN keysets must remain equal");
  assert.deepEqual(keysets[2], keysets[0], "Memory Center VI and ZH keysets must remain equal");
  assert.ok(keysets[0].length >= 130, "Memory catalogue must cover notes, reminders, history, filters and boundaries");
  for (const key of [
    "memory.priority.urgent",
    "memory.repeat.weekly",
    "memory.state.archived",
    "memory.form.contentLabel",
    "memory.filter.reminderSubmit",
    "memory.detail.restoreVersionConfirm",
    "memory.history.title",
    "memory.linked.title",
    "memory.reminder.createSubmit",
    "memory.activity.body"
  ]) {
    assert.ok(messages.vi[key] && messages.en[key] && messages.zh[key], "missing Memory locale copy: " + key);
  }
});

test("Memory Center uses localized chrome without changing workflow contracts", () => {
  for (const helperCall of [
    'memoryText("form.titleLabel"',
    'memoryText("filter.searchLabel"',
    'memoryText("detail.historyKicker"',
    'memoryText("history.title"',
    'memoryText("linked.title"',
    'memoryText("reminder.createTitle"',
    'memoryText("activity.title"'
  ]) {
    assert.ok(source.includes(helperCall), "Memory Center must use localized helper: " + helperCall);
  }
  for (const staleFixedCopy of [
    "Version history",
    "Linked reminders",
    "Private Web memory",
    "Privacy boundary",
    "Web-owned",
    "owner-scoped",
    "signed Web account",
    "Web view-only delivery",
    "Explicit status",
    "Audit-safe feed"
  ]) {
    assert.ok(!source.includes(staleFixedCopy), "mixed-language Memory Center copy remains: " + staleFixedCopy);
  }
  for (const contract of [
    'data-portal-action="memory-note-create"',
    'data-portal-action="memory-note-update"',
    'data-portal-action="memory-note-archive"',
    'data-portal-action="memory-note-restore"',
    'data-portal-action="memory-note-restore-version"',
    'data-portal-action="memory-note-filter"',
    'data-portal-action="memory-reminder-create"',
    'data-portal-action="memory-reminder-update"',
    'data-portal-action="memory-reminder-complete"',
    'data-portal-action="memory-reminder-pause"',
    'data-portal-action="memory-reminder-resume"',
    'data-portal-action="memory-reminder-cancel"',
    'data-portal-action="memory-reminder-filter"',
    'data-memory-note-id=',
    'data-memory-note-revision=',
    'data-memory-reminder-id=',
    'data-memory-reminder-revision='
  ]) {
    assert.ok(source.includes(contract), "Memory workflow contract missing: " + contract);
  }
});

test("Memory Center keeps fixed chrome separate from owner data", () => {
  assert.match(source, /String\(note\.title \|\| memoryText\("detail\.noteFallback"/);
  assert.match(source, /String\(item\.title \|\| memoryText\("reminder\.fallbackTitle"/);
  assert.match(source, /String\(item\.body \|\| memoryText\("reminder\.noBody"/);
  assert.match(source, /String\(item\.created_at \|\| "—"\)/);
  assert.match(source, /data-memory-note-id=/);
  assert.match(source, /data-memory-note-revision=/);
});
