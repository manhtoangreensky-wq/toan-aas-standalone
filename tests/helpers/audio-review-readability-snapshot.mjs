import assert from "node:assert/strict";
import {imageStudioPresentationHistoricalSource} from "./image-studio-presentation-historical.mjs";

const file = "static/portal/portal-theme.css";
const fail = "Unreviewed audio review readability";
const old = `.portal-page.portal-audio-hub-detail .portal-audio-hub-review-pack .portal-project-steps span,
.portal-page.portal-audio-hub-detail .portal-audio-hub-review-pack .portal-project-steps small {
  color: var(--portal-muted);
}`;
const addition = `.portal-page.portal-audio-hub-detail .portal-audio-hub-review-pack > .portal-project-steps > li > span > b,
.portal-page.portal-audio-hub-detail .portal-audio-hub-review-pack > .portal-project-steps > li > span > small {
  display: block;
}`;
const marker = ".portal-page.portal-audio-hub-detail .portal-audio-hub-review-pack > .portal-project-steps";
const count = (source, part) => source.split(part).length - 1;

// Historical input only; current CSS acceptance compares the full source to BASE plus the exact rule.
export function audioReviewReadabilityHistoricalSource(source, name) {
  assert.equal(typeof source, "string", fail);
  assert.equal(typeof name, "string", fail);
  source = imageStudioPresentationHistoricalSource(source, name);
  if (name !== file || !source.includes(marker)) return source;
  assert.equal(count(source, marker), 2, fail + " exact two selectors");
  assert.equal(count(source, old + "\n\n" + addition), 1, fail + " exact scoped rule and anchor");
  const result = source.replace(old + "\n\n" + addition, () => old);
  assert.equal(count(result, marker), 0, fail + " detached selector");
  return result;
}
