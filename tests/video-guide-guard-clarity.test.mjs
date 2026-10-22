import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");
const videoStart = source.indexOf("function renderVideoFactoryWorkflow");
const guideStart = source.indexOf("function renderSourceRightsGuide");
assert.ok(videoStart >= 0, "Video Factory renderer must remain present");
assert.ok(guideStart >= 0, "Source Rights renderer must remain present");

test("Video and rights-guide guards keep the action message without technical chips", () => {
  const videoEnd = source.indexOf("\n  function ", videoStart + 10);
  const guideEnd = source.indexOf("\n  function ", guideStart + 10);
  assert.doesNotMatch(source.slice(videoStart, videoEnd), /portal-state-meta/);
  assert.doesNotMatch(source.slice(guideStart, guideEnd), /portal-state-meta/);
});
