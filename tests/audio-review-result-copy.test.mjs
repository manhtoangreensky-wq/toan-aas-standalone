import test from "node:test";
import assert from "node:assert/strict";
import {sources, runtime, collection, context, freeze, IDS}
  from "./helpers/media-collection-locale-runtime.mjs";
import {CONTRACT, ACTION, ROUTE, receipt} from "./helpers/audio-review-feedback-runtime.mjs";

const source = sources();
const esc = value => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
const copy = (short, locale) => CONTRACT.staticRows.find(row => row.short === short)[locale];
function render(app, {raw = receipt(), row = collection(), capability = true, canView = true, route = ROUTE} = {}) {
  const ctx = context({canView, row, overrides: {path: route, audioHubReviewPack: raw}});
  ctx.capabilities[ACTION] = capability;
  const before = JSON.stringify({raw, row, ctx});
  freeze(raw); freeze(row); freeze(ctx);
  const whole = app.call("renderMediaWorkspaceDetail", app.page(route), ctx);
  assert.equal(JSON.stringify({raw, row, ctx}), before, "Renderer cannot mutate raw server/caller DTOs");
  assert.deepEqual(app.attempts(), [], "Rendering is pure, without HTTP/storage/timers/dispatch/navigation");
  const start = whole.indexOf('<section class="portal-card portal-card-pad portal-audio-hub-review-pack"');
  if (start < 0) return {whole, review: ""};
  const last = whole.indexOf(`data-portal-action="${ACTION}"`, start);
  assert.ok(last > start, "Review control occurs inside actual Hub detail");
  const end = whole.indexOf("</button></div></section>", last);
  assert.ok(end > last, "Complete review section terminator");
  return {whole, review: whole.slice(start, end + "</button></div></section>".length)};
}
function controls(markup, disabled = false) {
  assert.equal((markup.match(/data-audio-hub-review-pack-status/g) || []).length, 1);
  assert.match(markup, /tabindex="-1" role="status" aria-live="polite" aria-atomic="true"/);
  assert.match(markup, new RegExp(`data-media-collection-id="${IDS[0]}"`));
  assert.match(markup, new RegExp(`data-portal-action="${ACTION}" data-portal-route="${ROUTE}"`));
  assert.match(markup, /data-media-collection-revision="7"/);
  const button = markup.match(new RegExp(`<button[^>]*data-portal-action="${ACTION}"[^>]*>`));
  assert.ok(button); assert.equal(/\sdisabled(?:\s|>)/.test(button[0]), disabled);
  assert.doesNotMatch(markup, /<audio\b|<video\b|<iframe\b|<script\b|src=|source_url|download_url/i);
}
function items(markup) {
  const checks = markup.match(/<ol class="portal-project-steps">([\s\S]*?)<\/ol>/)?.[1] || "";
  const cautions = markup.match(/<section class="portal-media-policy">[\s\S]*?<ul>([\s\S]*?)<\/ul><\/section>/)?.[1] || "";
  return {checks, cautions};
}

for (const locale of ["vi", "en", "zh"]) {
  test(`${locale}/full physical Hub detail translates all11 raw stock result strings, preserving four checks and three cautions`, () => {
    const app = runtime(source, locale), raw = freeze(receipt());
    const {whole, review} = render(app, {raw}), actual = items(review);
    assert.match(whole, /portal-audio-hub-detail/); controls(review);
    assert.equal((actual.checks.match(/<li>/g) || []).length, 4);
    assert.equal((actual.cautions.match(/<li>/g) || []).length, 3);
    assert.match(review, /<strong>1\.<\/strong>/); assert.match(review, /<strong>4\.<\/strong>/);
    assert.equal(raw.review_pack.checks.length, 4); assert.equal(raw.review_pack.cautions.length, 3);
    assert.deepEqual(raw.review_pack.checks.map(row => row.id),
      ["brief_originality", "reference_metadata", "mix_accessibility", "release_handoff"]);
    for (const row of CONTRACT.resultRows) {
      assert.ok(review.includes(esc(row[locale])), row.key + " independent expected literal");
      if (row.old !== row[locale]) assert.ok(!review.includes(esc(row.old)), "Old stock absent: " + row.key);
    }
    assert.ok(review.includes(esc(copy("review.state.needsMetadata", locale))));
    assert.ok(review.includes("3 " + esc(copy("review.references", locale))));
    assert.match(review, /<span>1 [^<]+<\/span><span>1 [^<]+<\/span>/);
  });
  test(`${locale}/all11 selected static overrides appear in the relevant actual renderer states`, () => {
    const app = runtime(source, locale), variants = [];
    variants.push(render(app).review, render(app, {raw: {}}).review);
    for (const state of ["needs_reference_metadata", "human_review_required", "unknown_state"]) {
      const raw = receipt(); raw.review_pack.review_state = state;
      variants.push(render(app, {raw}).review);
    }
    const all = variants.join("\n");
    for (const row of CONTRACT.staticRows) assert.ok(all.includes(esc(row[locale])), row.key);
  });
  test(`${locale}/empty review is honest and has no empty checklist/caution frames`, () => {
    const app = runtime(source, locale), {review} = render(app, {raw: {}});
    controls(review);
    assert.equal(items(review).checks, ""); assert.equal(items(review).cautions, "");
    assert.doesNotMatch(review, /<ol\b|<ul\b|<section class="portal-media-policy"/);
    assert.ok(review.includes(esc(copy("review.empty", locale))));
  });
}

test("renderer binding uses whole physical portal+i18n, one observation insertion and zero replaced functions", () => {
  const app = runtime(source, "en"), binding = app.binding;
  assert.equal(binding.exposureCount, 1); assert.equal(binding.replacedProductionFunctions, 0);
  assert.equal(binding.executedPortalBytes, binding.physicalPortalBytes + binding.exposureBytes);
  assert.notEqual(binding.hashes.portal, binding.executedPortalHash);
  const {whole, review} = render(app);
  assert.ok(whole.length > review.length, "Actual parent detail is rendered, not an extracted production function");
  assert.deepEqual(app.attempts(), []);
});
test("missing translator uses the independent new Vietnamese result and static fallback copy", () => {
  const app = runtime(source, "en"); app.missingTranslator();
  const variants = [render(app).review, render(app, {raw: {}}).review];
  for (const state of ["human_review_required", "unknown_state"]) {
    const raw = receipt(); raw.review_pack.review_state = state; variants.push(render(app, {raw}).review);
  }
  const markup = variants.join("\n");
  for (const row of [...CONTRACT.resultRows, ...CONTRACT.staticRows]) {
    assert.ok(markup.includes(esc(row.vi)), "Vietnamese fallback: " + row.key);
  }
});
const rawValues = ["CUSTOMER Facebook TikTok & audio", "constructor", "toString", "__proto__",
  "<img src=x onerror='literal'> & \"customer\"", "prefix " + CONTRACT.resultRows[0].old,
  CONTRACT.resultRows[0].old + " suffix", 42, true, {customer: "value"}, ["customer", "audio"]];
for (const value of rawValues) test(`custom/typed result ${JSON.stringify(value)} preserves String and escaping, not id or substring translation`, () => {
  const app = runtime(source, "en"), raw = receipt();
  raw.review_pack.checks[0].label = value; raw.review_pack.checks[0].note = value;
  raw.review_pack.cautions[0] = value;
  const {review} = render(app, {raw: freeze(raw)}), actual = items(review), wanted = esc(String(value));
  assert.ok(actual.checks.includes(`<b>${wanted}</b><small>${wanted}</small>`));
  assert.ok(actual.cautions.includes(`<li>${wanted}</li>`));
  assert.doesNotMatch(review, /<img\b|onerror='/);
});
for (const value of ["", 0, false, null, undefined]) test(`falsy result ${String(value)} preserves the existing fallback/empty rules`, () => {
  const app = runtime(source, "vi"), raw = receipt();
  raw.review_pack.checks[0].label = value; raw.review_pack.checks[0].note = value;
  raw.review_pack.cautions[0] = value;
  const {review} = render(app, {raw: freeze(raw)}), actual = items(review);
  assert.match(actual.checks, /<b>Rà soát<\/b><small><\/small>/);
  assert.ok(actual.cautions.includes("<li></li>"));
});
test("stock strings are selected by exact value, never by check id or substring", () => {
  const app = runtime(source, "en"), raw = receipt();
  raw.review_pack.checks[0].id = "customer_id";
  raw.review_pack.checks[1].label = "CUSTOMER label with known reference_metadata id";
  const {review} = render(app, {raw: freeze(raw)});
  assert.ok(review.includes(esc(CONTRACT.resultRows[0].en)), "Exact stock translates independently of id");
  assert.ok(review.includes("CUSTOMER label with known reference_metadata id"));
});
for (const spec of [
  {name: "capability false", capability: false}, {name: "capability truthy string", capability: "true"},
  {name: "capability truthy number", capability: 1}, {name: "archived", row: collection({state: "archived"})},
  {name: "guarded policy", row: collection({policy: {status: "guarded", marker: "originality"}})}
]) test(`${spec.name}: control remains visible and disabled, without inventing a review`, () => {
  const app = runtime(source, "en"), {review} = render(app, {...spec, raw: {}});
  controls(review, true); assert.doesNotMatch(review, /<ol\b|<section class="portal-media-policy"/);
});
for (const patch of [{collection_id: IDS[1]}, {revision: 8}, {review_pack: null}]) {
  test(`mismatched/missing raw receipt ${JSON.stringify(patch)} stays an empty review`, () => {
    const app = runtime(source, "en"), {review} = render(app, {raw: {...receipt(), ...patch}});
    controls(review); assert.doesNotMatch(review, /<ol\b|<ul\b/);
    assert.ok(review.includes(esc(copy("review.empty", "en"))));
  });
}
test("non-Hub routes and denied collection access do not grow meaningless review frames", () => {
  const app = runtime(source, "en");
  const library = render(app, {route: "/media-workspace/" + IDS[0]});
  assert.equal(library.review, ""); assert.doesNotMatch(library.whole, /data-audio-hub-review-pack-status/);
  const denied = render(app, {canView: false});
  assert.equal(denied.review, ""); assert.doesNotMatch(denied.whole, /data-audio-hub-review-pack-status/);
  assert.deepEqual(app.attempts(), []);
});
test("catalogue contains all31 literal rows/93 values, equal locale keys and only the intended20 new keys", () => {
  const app = runtime(source, "vi");
  assert.equal(CONTRACT.copyRows.length, 31);
  assert.equal(new Set(CONTRACT.copyRows.map(row => row.key)).size, 31);
  const keysets = ["vi", "en", "zh"].map(locale => Object.keys(app.messages[locale]).sort());
  assert.deepEqual(keysets[1], keysets[0]); assert.deepEqual(keysets[2], keysets[0]);
  for (const locale of ["vi", "en", "zh"]) for (const row of CONTRACT.copyRows) {
    assert.equal(app.messages[locale][row.key], row[locale], row.key + "/" + locale);
    assert.equal(typeof row[locale], "string"); assert.ok(row[locale].length > 0);
  }
  assert.equal(CONTRACT.feedback.length + CONTRACT.resultRows.length, 20);
  assert.equal(CONTRACT.staticRows.length, 11);
});
