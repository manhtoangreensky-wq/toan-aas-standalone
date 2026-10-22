import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");
const start = source.indexOf("  function renderChatWorkspaceBoundary(context)");
const end = source.indexOf("\n  function renderChatWorkspaceCards", start);
assert.ok(start >= 0 && end > start, "Chat boundary renderer must remain present");

test("Chat Workspace boundary uses one useful capability explanation", () => {
  const renderer = source.slice(start, end);
  assert.match(renderer, /portal-chat-workspace-guard-list/);
  assert.match(renderer, /Máy chủ chưa công bố capability gửi request/);
  assert.doesNotMatch(renderer, /<span><strong>Provider \/ Bot|<span><strong>Wallet \/ payment|<span><strong>Job \/ output/);
});
