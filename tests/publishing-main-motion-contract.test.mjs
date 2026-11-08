import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { renderChild } from "./helpers/publishing-child-render.mjs";

const portal = fs.readFileSync("static/portal/portal.js", "utf8");

test("publishing workspace skips whole-main entry while preserving its real renderer", () => {
  assert.match(portal, /const publishingMotionRoute = page\.path === "\/publishing" && page\.layout === "autopost-hub";/);
  assert.match(portal, /main\.dataset\.portalMotionSkipEnter = landingMotionRoute \|\| dashboardMotionRoute \|\| publishingMotionRoute \|\|/);
  const result = renderChild("vi", "/publishing", {});
  assert.match(result.html, /portal-autopost-hub/);
  assert.match(result.text, /Đăng bài|Chuẩn bị|rà soát/u);
});

test("publishing workspace keeps language projection in English and Chinese", () => {
  const en = renderChild("en", "/publishing", {});
  const zh = renderChild("zh", "/publishing", {});
  assert.doesNotMatch(en.text, /Đăng bài|Chuẩn bị|rà soát/u);
  assert.match(zh.text, /发布|内容|审核|工作区/u);
});
