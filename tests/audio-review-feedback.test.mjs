import test from "node:test";
import assert from "node:assert/strict";
import {ACTION, CONTRACT, IDS, ROUTE, boundary, freeze, plain, receipt, reply, runtime}
  from "./helpers/audio-review-feedback-runtime.mjs";

const expected = (short, locale) => CONTRACT.feedback.find(row => row.short === short)[locale];
const server = short => CONTRACT.serverRows.find(row => row.short === short).source;
function install(app, response = reply()) { app.respond(() => response); }
function quiet(app, posts = 0) {
  const actual = app.observe();
  assert.equal(actual.network.length, posts, "No retry or unrelated HTTP");
  assert.deepEqual(actual.forbidden, [], "No network/storage/navigation/provider boundary escaped");
  return actual;
}
function completed(app, output, posts = 1) {
  const actual = quiet(app, posts);
  assert.deepEqual(actual.state.audioHubReviewPack, output);
  assert.equal(actual.control.disabled, false);
  assert.deepEqual(actual.busy.slice(-2), [{value: "true", disabled: true}, {value: "false", disabled: false}]);
  return actual;
}

for (const locale of ["vi", "en", "zh"]) {
  const localCases = [
    {short: "review.route", details: {route: "/media-workspace/" + IDS[0]}, posts: 0},
    {short: "review.notReady", setup: app => app.patch({capabilities: {[ACTION]: false}}), posts: 0},
    {short: "review.invalidBoundary", response: reply({...boundary(), provider_called: true}, {status: "guarded"}), posts: 1},
    {short: "review.invalidResult", response: reply({...receipt(), revision: 8}), posts: 1}
  ];
  for (const spec of localCases) test(`${locale}/${spec.short}: real dispatcher local throw`, async () => {
    const app = runtime(locale); spec.setup?.(app); install(app, spec.response);
    const text = await app.dispatch(spec.details);
    const actual = quiet(app, spec.posts);
    assert.equal(actual.toasts.at(-1).attributes.role, "alert");
    assert.equal(text, expected(spec.short, locale));
  });
  for (const guarded of [false, true]) test(`${locale}/${guarded ? "VM_ONLY_ACKNOWLEDGED_GUARDED" : "draft"}/fallback`, async () => {
    const app = runtime(locale), output = guarded ? boundary() : receipt();
    install(app, reply(output, {status: guarded ? "guarded" : "draft"}));
    const text = await app.dispatch(), actual = completed(app, guarded ? {} : output);
    assert.equal(actual.toasts.at(-1).attributes.role, "status");
    assert.equal(text, expected(guarded ? "review.needsChanges" : "review.ready", locale));
    assert.equal(actual.pendingRAF, guarded ? 0 : 1);
  });
  test(`${locale}/real stock success uses its truthy server message`, async () => {
    const app = runtime(locale), output = freeze(receipt()), before = JSON.stringify(output);
    install(app, reply(output, {message: server("review.ready")}));
    const text = await app.dispatch(), actual = completed(app, output);
    assert.deepEqual(actual.merges.map(row => row.audioHubReviewPack), [{}, output]);
    assert.equal(actual.pendingRAF, 1); assert.deepEqual(actual.focus, []);
    app.flushRAF();
    assert.deepEqual(app.observe().focus, [{selector: "review-status", options: {preventScroll: true}}]);
    assert.equal(JSON.stringify(output), before);
    assert.equal(text, expected("review.ready", locale));
  });
  for (const short of ["review.archived", "review.originality"]) {
    test(`${locale}/${short}: actual backend ok:false guarded envelope throws through real api and outer catch`, async () => {
      const app = runtime(locale);
      install(app, reply(boundary(), {ok: false, status: "guarded", message: server(short)}));
      const text = await app.dispatch(), actual = completed(app, {});
      assert.equal(actual.toasts.at(-1).attributes.role, "alert", "Not the acknowledged warning branch");
      assert.equal(actual.pendingRAF, 0); assert.deepEqual(actual.focus, []);
      assert.equal(text, expected(short, locale));
    });
  }
  for (const row of CONTRACT.serverRows.filter(row => row.short === "review.error")) {
    test(`${locale}/generic API stock ${row.source}`, async () => {
      const app = runtime(locale);
      install(app, reply(boundary(), {ok: false, status: "guarded", message: row.source}));
      assert.equal(await app.dispatch(), expected("review.error", locale));
      completed(app, {});
    });
  }
}

test("complete physical integration+i18n binding, exact POST/header/DTO and no implicit acknowledgement", async () => {
  const app = runtime("en"), output = freeze(receipt());
  const binding = app.binding;
  assert.equal(binding.exposureCount, 1); assert.equal(binding.replacedProductionFunctions, 0);
  assert.equal(binding.executedIntegrationBytes, binding.physicalIntegrationBytes + binding.exposureBytes);
  assert.notEqual(binding.hashes.integration, binding.executedIntegrationHash);
  install(app, reply(output, {message: "CUSTOMER_RESULT"})); await app.dispatch();
  const actual = completed(app, output), request = actual.network[0];
  assert.equal(request.path, `/api/v1/media-workspace/collections/${IDS[0]}/review-pack`);
  assert.equal(request.method, "POST"); assert.deepEqual(request.body, {expected_revision: 7});
  assert.equal(request.credentials, "same-origin"); assert.equal(request.cache, "no-store");
  assert.equal(request.headers.accept, "application/json");
  assert.equal(request.headers["content-type"], "application/json");
  assert.equal(request.headers["x-csrf-token"], "SYNTHETIC_AUDIO_REVIEW_ONLY");
  assert.match(request.headers["x-request-id"], /^web-[a-f0-9]{32}$/);
  assert.deepEqual(actual.state.mediaCollectionDetail.collection,
    {id: IDS[0], title: "SYNTHETIC COLLECTION", state: "active", revision: 7, policy: {status: "clear", marker: null}});
});

for (const mode of ["missing", "key", "empty", "number"]) {
  for (const kind of ["route", "success", "guarded", "serverError"]) {
    test(`${mode}/${kind}: unusable translator uses independent new Vietnamese fallback`, async () => {
      const app = runtime("en"); app.translation(mode);
      if (kind === "success") install(app, reply());
      if (kind === "guarded") install(app, reply(boundary(), {status: "guarded"}));
      if (kind === "serverError") install(app, reply(boundary(), {ok: false, status: "guarded", message: server("review.archived")}));
      const short = {route: "review.route", success: "review.ready", guarded: "review.needsChanges",
        serverError: "review.archived"}[kind];
      const text = await app.dispatch(kind === "route" ? {route: "/audio-hub"} : {});
      quiet(app, kind === "route" ? 0 : 1);
      assert.equal(text, expected(short, "vi"));
    });
  }
}

const customMessages = ["CUSTOMER Facebook TikTok audio", "constructor", "toString", "__proto__",
  "<img src=x onerror='customer'> & <script>literal</script>", "prefix " + server("review.archived"),
  server("review.ready") + " customer suffix", true, 42, ["custom", "values"], {custom: "message"}];
for (const value of customMessages) for (const kind of ["draft", "acknowledgedGuarded", "error"]) {
  test(`${kind}/raw message/${JSON.stringify(value)} stays plain literal`, async () => {
    const app = runtime("en"), output = freeze(receipt());
    const error = kind === "error", guarded = kind !== "draft";
    install(app, reply(guarded ? boundary() : output,
      {ok: !error, status: guarded ? "guarded" : "draft", message: freeze(value)}));
    const text = await app.dispatch(), actual = completed(app, guarded ? {} : output);
    assert.equal(text, String(value).trim());
    assert.equal(actual.toasts.at(-1).attributes.role, error ? "alert" : "status");
    assert.deepEqual(actual.forbidden, [], "Hostile strings never reach HTML sinks");
  });
}
test("unknown raw thrown error remains verbatim and a mutation is never retried", async () => {
  const app = runtime("zh");
  app.respond(() => { throw Error("CUSTOMER <b>raw network error</b>"); });
  assert.equal(await app.dispatch(), "CUSTOMER <b>raw network error</b>"); completed(app, {});
});
test("real api rejects ok:false even at HTTP 200 and preserves payload and status", async () => {
  const app = runtime("en"), response = freeze(reply(boundary(),
    {ok: false, status: "guarded", message: server("review.archived")}));
  install(app, response);
  await assert.rejects(app.call("api", `/media-workspace/collections/${IDS[0]}/review-pack`,
    {method: "POST", headers: {"Content-Type": "application/json"}, body: '{"expected_revision":7}'}),
  error => error.message === server("review.archived") && error.status === 200
    && JSON.stringify(error.payload) === JSON.stringify(response.payload));
  const actual = quiet(app, 1); assert.deepEqual(actual.toasts, []); assert.deepEqual(actual.merges, []);
});

const invalidRoutes = [{route: "/audio-hub"}, {route: "/audio-hub/" + IDS[1]},
  {route: "/audio-hub/" + IDS[0] + "/extra"}, {mediaCollectionId: "not-a-uuid"},
  {mediaCollectionRevision: 0}, {mediaCollectionRevision: -1}, {mediaCollectionRevision: 1.5},
  {mediaCollectionRevision: "bogus"}];
for (const detail of invalidRoutes) test(`invalid route/id/revision ${JSON.stringify(detail)} makes no HTTP`, async () => {
  const app = runtime(); await app.dispatch(detail);
  const actual = quiet(app); assert.equal(actual.merges.length, 0); assert.deepEqual(actual.busy, []);
});
for (const value of [false, "true", 1, null, {}, []]) test(`capability ${JSON.stringify(value)} is not strict true`, async () => {
  const app = runtime(); app.patch({capabilities: {[ACTION]: value}}); await app.dispatch();
  const actual = quiet(app); assert.equal(actual.merges.length, 0); assert.deepEqual(actual.busy, []);
});
for (const patch of [{id: IDS[1]}, {revision: 8}, {state: "archived"}, {policy: {status: "guarded"}}]) {
  test(`current collection guard ${JSON.stringify(patch)} makes no HTTP`, async () => {
    const app = runtime(), before = app.observe().state.mediaCollectionDetail;
    app.patch({mediaCollectionDetail: {...before, collection: {...before.collection, ...patch}}});
    await app.dispatch(); quiet(app);
  });
}

const malformed = [
  ["extra top key", value => { value.extra = false; }],
  ["wrong collection", value => { value.collection_id = IDS[1]; }],
  ["wrong revision", value => { value.revision = 8; }],
  ["wrong boundary execution", value => { value.execution = "approved"; }],
  ["nonboolean boundary", value => { value.provider_called = 0; }],
  ["missing boundary", value => { delete value.rights_verified; }],
  ["policy marker", value => { value.review_pack.policy.marker = "clear"; }],
  ["policy status", value => { value.review_pack.policy.status = "approved"; }],
  ["summary total", value => { value.review_pack.reference_summary.total = 4; }],
  ["summary count type", value => { value.review_pack.reference_summary.music = "1"; }],
  ["summary bound", value => { value.review_pack.reference_summary.favorite = 4; }],
  ["summary boolean", value => { value.review_pack.reference_summary.collection_rights_note_declared = 1; }],
  ["missing check", value => { value.review_pack.checks.pop(); }],
  ["wrong check order", value => { value.review_pack.checks.reverse(); }],
  ["wrong check state", value => { value.review_pack.checks[0].state = "approved"; }],
  ["label type", value => { value.review_pack.checks[0].label = 42; }],
  ["note too short", value => { value.review_pack.checks[0].note = "x"; }],
  ["unsafe control note", value => { value.review_pack.checks[0].note = "CUSTOMER \u0001 note"; }],
  ["caution count", value => { value.review_pack.cautions.pop(); }],
  ["caution type", value => { value.review_pack.cautions[0] = {}; }],
  ["review state", value => { value.review_pack.review_state = "release_approved"; }]
];
test("actual guards accept the exact immutable current receipt and all-false boundary", () => {
  const app = runtime(), output = freeze(receipt());
  assert.equal(app.call("audioHubReviewPackBoundaryIsSafe", freeze(boundary())), true);
  assert.equal(app.call("audioHubReviewPackResultIsSafe", output, IDS[0], 7), true);
  for (const [key] of Object.entries(boundary()).filter(([key]) => key !== "execution")) {
    assert.equal(app.call("audioHubReviewPackBoundaryIsSafe", {...boundary(), [key]: true}), false, key);
  }
});
for (const [name, mutate] of malformed) test(`malformed receipt/${name} fails closed without merge or focus`, async () => {
  const app = runtime(), output = receipt(); mutate(output); freeze(output);
  assert.equal(app.call("audioHubReviewPackResultIsSafe", output, IDS[0], 7), false);
  install(app, reply(output)); await app.dispatch();
  const actual = completed(app, {}); assert.equal(actual.pendingRAF, 0); assert.deepEqual(actual.focus, []);
});

for (const kind of ["route", "logout", "revision", "disabled"]) {
  test(`delayed successful response after ${kind} stays silent and cannot clear another view's busy state`, async () => {
    const app = runtime(), output = freeze(receipt()); let finish;
    app.respond(() => new Promise(resolve => { finish = resolve; }));
    const pending = app.dispatch(); assert.equal(app.observe().network.length, 1);
    if (kind === "route") app.path("/audio-hub/" + IDS[1]);
    if (kind === "logout") app.patch({session: {authenticated: false, csrfToken: ""}});
    if (kind === "disabled") app.patch({mediaWorkspaceEnabled: false});
    if (kind === "revision") {
      const detail = app.observe().state.mediaCollectionDetail;
      app.patch({mediaCollectionDetail: {...detail, collection: {...detail.collection, revision: 8}}});
    }
    finish(reply(output, {message: "CUSTOMER_OLD"})); await pending;
    const actual = quiet(app, 1);
    assert.deepEqual(actual.toasts, []); assert.deepEqual(actual.state.audioHubReviewPack, {});
    assert.equal(actual.pendingRAF, 0); assert.deepEqual(actual.focus, []);
    assert.deepEqual(actual.busy, [{value: "true", disabled: true}]);
  });
}
test("overlapping requests accept only the newest and old finally cannot unlock it", async () => {
  const app = runtime(), resolvers = [];
  app.respond(() => new Promise(resolve => resolvers.push(resolve)));
  const older = app.dispatch(), newer = app.dispatch();
  assert.equal(resolvers.length, 2);
  resolvers[0](reply(receipt(), {message: "OLD"})); await older;
  assert.deepEqual(app.observe().toasts, []); assert.equal(app.observe().control.disabled, true);
  const output = receipt(); output.review_pack.reference_summary.favorite = 2;
  resolvers[1](reply(freeze(output), {message: "NEW"})); await newer;
  const actual = completed(app, output, 2);
  assert.equal(actual.toasts.length, 1); assert.equal(actual.toasts[0].text, "NEW");
  assert.deepEqual(actual.busy.map(row => row.value), ["true", "true", "false"]);
});
test("queued RAF rechecks route, session and revision before focusing", async () => {
  for (const kind of ["route", "logout", "revision"]) {
    const app = runtime(); install(app, reply(receipt(), {message: "CURRENT"})); await app.dispatch();
    assert.equal(app.observe().pendingRAF, 1);
    if (kind === "route") app.path("/audio-hub/" + IDS[1]);
    if (kind === "logout") app.patch({session: {authenticated: false}});
    if (kind === "revision") {
      const detail = app.observe().state.mediaCollectionDetail;
      app.patch({mediaCollectionDetail: {...detail, collection: {...detail.collection, revision: 8}}});
    }
    app.flushRAF(); assert.deepEqual(app.observe().focus, []); quiet(app, 1);
  }
});
for (const row of CONTRACT.serverRows) {
  test(`non-review outer catch leaves ${row.source} unchanged`, async () => {
    const app = runtime("en"), stock = row.source;
    // A browser-event value coercion throws locally before this other action
    // can emit HTTP; no production function or error handler is replaced.
    const badId = {toString() { throw Error(stock); }};
    assert.equal(await app.dispatch({mediaCollectionId: badId}, "media-collection-compose"), stock);
    const actual = quiet(app); assert.equal(actual.toasts.at(-1).attributes.role, "alert");
    assert.equal(plain(actual).network.length, 0);
  });
}
