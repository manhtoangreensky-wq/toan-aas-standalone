import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");
const guideStart = source.indexOf("function renderGuideCenter");
const videoStart = source.indexOf("function renderVideoFactoryWorkflow");
assert.ok(guideStart >= 0 && videoStart >= 0, "Guide and Video Factory renderers must remain present");

test("Guide and Video Factory intros do not show zero-only technical metrics", () => {
  const guideEnd = source.indexOf("\n  function ", guideStart + 10);
  const videoEnd = source.indexOf("\n  function ", videoStart + 10);
  const guide = source.slice(guideStart, guideEnd);
  const video = source.slice(videoStart, videoEnd);
  assert.doesNotMatch(guide, /execution_count/);
  assert.doesNotMatch(video, /Provider call|Customer publish/);
  assert.match(video, /Bước có chủ đích/);
});
