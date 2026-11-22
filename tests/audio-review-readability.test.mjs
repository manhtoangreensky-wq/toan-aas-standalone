import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {sources, runtime, collection, context} from "./helpers/media-collection-locale-runtime.mjs";
import {receipt, ACTION, ROUTE} from "./helpers/audio-review-feedback-runtime.mjs";
import {audioReviewReadabilityHistoricalSource as historical} from "./helpers/audio-review-readability-snapshot.mjs";
import {imageStudioPresentationHistoricalSource} from "./helpers/image-studio-presentation-historical.mjs";

const base = "cd9c5c14263e1397531056e318a9f46394a8562d";
const file = "static/portal/portal-theme.css";
const old = `.portal-page.portal-audio-hub-detail .portal-audio-hub-review-pack .portal-project-steps span,
.portal-page.portal-audio-hub-detail .portal-audio-hub-review-pack .portal-project-steps small {
  color: var(--portal-muted);
}`;
const addition = `.portal-page.portal-audio-hub-detail .portal-audio-hub-review-pack > .portal-project-steps > li > span > b,
.portal-page.portal-audio-hub-detail .portal-audio-hub-review-pack > .portal-project-steps > li > span > small {
  display: block;
}`;
const lf = value => value.replace(/\r\n/g, "\n");

test("theme CSS contains only the scoped review readability change", () => {
  const before = lf(execFileSync("git", ["show", base + ":" + file], {encoding: "utf8", maxBuffer: 20e6}));
  const current = imageStudioPresentationHistoricalSource(lf(fs.readFileSync(file, "utf8")), file);
  assert.equal(before.split(old).length - 1, 1);
  assert.equal(current, before.replace(old, () => old + "\n\n" + addition));
  assert.equal(historical(current, file), before);
  assert.equal(historical(before, file), before);
  assert.equal(historical("/* customer */\n" + current, file), "/* customer */\n" + before);
  assert.throws(() => historical(current.replace(addition, addition.replace("display: block;", "display: inline;")), file), /Unreviewed audio review readability/);
  assert.throws(() => historical(current + "\n" + addition, file), /Unreviewed audio review readability/);
});

for (const locale of ["vi", "en", "zh"]) {
  test(`${locale}: actual review renderer keeps four label and note pairs in the scoped structure`, () => {
    const app = runtime(sources(), locale), raw = receipt(), row = collection();
    const ctx = context({row, overrides: {path: ROUTE, audioHubReviewPack: raw}});
    ctx.capabilities[ACTION] = true;
    const html = app.call("renderMediaWorkspaceDetail", app.page(ROUTE), ctx);
    const review = html.split('class="portal-card portal-card-pad portal-audio-hub-review-pack"')[1];
    assert.ok(review);
    const steps = review.match(/<ol class="portal-project-steps">([\s\S]*?)<\/ol>/)?.[1] || "";
    assert.equal((steps.match(/<li><strong>\d+\.<\/strong><span><b>[^<]+<\/b><small>[^<]+<\/small><\/span><\/li>/g) || []).length, 4);
    assert.equal((review.match(/data-portal-action="audio-hub-review-pack-compose"/g) || []).length, 1);
  });
}
