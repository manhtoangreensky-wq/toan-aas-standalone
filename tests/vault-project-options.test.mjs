import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import {fileURLToPath} from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = fs.readFileSync(path.join(ROOT, "static/portal/integration.js"), "utf8");
const ID = "11111111-1111-4111-8111-111111111111";
const TITLE = 'Customer Facebook TikTok media studio <img src=x onerror="alert(1)"> &';
const item = () => ({id: ID, title: TITLE, state: "active"});
const payload = (items = [item()]) => ({ok: true, status: "read_only",
  data: {items, limit: 50, offset: 0, has_more: false, next_offset: null}});
const json = value => JSON.parse(JSON.stringify(value));

function actualFunction(name) {
  const starts = [`  function ${name}(`, `  async function ${name}(`];
  const found = starts.map(prefix => source.indexOf(prefix)).filter(index => index >= 0);
  assert.equal(found.length, 1, "Unique real function: " + name);
  const start = found[0], end = source.indexOf("\n  }", start);
  assert.ok(end > start, name);
  return source.slice(start, end + 4);
}

function runtime({route = "/asset-vault", enabled = true, signed = true} = {}) {
  let state = {path: route, projects: [], session: {authenticated: signed},
    projectListing: {filters: {q: "OLD CUSTOMER QUERY", state: "archived"},
      pagination: {offset: 200}}, pageStates: {"/asset-vault": "ready"}};
  const reads = [], merges = [], pending = [];
  const window = {location: {pathname: route}, TOANAASPortal: {mount: value => merges.push(json(value))}};
  Object.defineProperty(window, "__TOAN_AAS_PORTAL__", {get: () => state, set: value => {state = value;}});
  const sandbox = vm.createContext({window, URLSearchParams,
    api: request => {reads.push(request); return new Promise((resolve, reject) => pending.push({resolve, reject}));}});
  const declarations = ["PROJECT_LIST_STATES", "PROJECT_LIST_LIMIT", "PROJECT_MAX_LIST_OFFSET"].map(name => {
    const line = source.split("\n").filter(value => value.startsWith("  const " + name + " = "));
    assert.equal(line.length, 1); return line[0];
  }).join("\n");
  const names = ["base", "currentPortalPath", "validProjectId", "projectFilterPayload", "projectListOffset",
    "projectListPath", "projectRouteUsesListView", "projectListingProjection", "projectCenterRequestIsCurrent",
    "merge", "hydrateProjects"];
  const dispatch = source.split("\n").filter(line => line.includes('if (account && ([')
    && line.endsWith("await hydrateProjects();"));
  assert.equal(dispatch.length, 1, "Unique existing bootstrap dispatch");
  const detectors = [...new Set(dispatch[0].match(/\bisNative[A-Za-z]+Path\b/g) || [])];
  vm.runInContext([
    declarations,
    "let projectCenterListHydrationEpoch=0, projectCenterSessionEpoch=0;",
    "const promptStudioComposeLockRoute='';",
    ...detectors.map(name => `const ${name}=()=>false;`),
    ...names.map(actualFunction),
    `window.probe={dispatch:async(account,assetVaultEnabled)=>{const currentPath=currentPortalPath();${dispatch[0]}\n},
      read:(...args)=>hydrateProjects(...args),epoch:()=>{projectCenterListHydrationEpoch++;},
      session:()=>{projectCenterSessionEpoch++;}};`
  ].join("\n"), sandbox);
  return {reads, merges, pending, get state() {return state;},
    dispatch: () => window.probe.dispatch(signed ? {id: "SYNTHETIC_ACCOUNT"} : null, enabled),
    read: (...args) => window.probe.read(...args),
    mutate: kind => {
      if (kind === "epoch") window.probe.epoch();
      else if (kind === "session") window.probe.session();
      else if (kind === "route") state.path = "/dashboard";
      else if (kind === "logout") state.session = {authenticated: false};
      else throw Error("Unknown mutation");
    }};
}

test("enabled signed Vault bootstrap reads its own project options without inherited board filters", async () => {
  const r = runtime(), task = r.dispatch();
  assert.deepEqual(r.reads, ["/projects?limit=50&offset=0"]);
  const response = payload(), before = JSON.stringify(response);
  r.pending[0].resolve(response); await task;
  assert.equal(JSON.stringify(response), before);
  assert.deepEqual(json(r.state.projects), [item()]);
  assert.equal(r.state.projectCenterReadState, "ready");
  assert.deepEqual(json(r.state.projectListing.filters), {q: "", state: "all"});
  assert.equal(r.state.projectListing.pagination.offset, 0);
  assert.equal(r.merges.length, 1);
});

for (const row of [
  {route: "/asset-vault", enabled: false, signed: true},
  {route: "/asset-vault", enabled: true, signed: false},
  {route: "/asset-vault", enabled: false, signed: false},
  {route: "/asset-vault/unknown", enabled: true, signed: true},
  {route: "/account", enabled: true, signed: true},
  {route: "/pricing", enabled: true, signed: true}
]) test("unrelated, disabled or guest bootstrap adds no project read: " + JSON.stringify(row), async () => {
  const r = runtime(row); await r.dispatch();
  assert.deepEqual(r.reads, []); assert.deepEqual(r.merges, []);
  assert.deepEqual(json(r.state.projects), []);
});

for (const route of ["/projects", "/project-packages", "/workspace", "/dashboard",
  "/media-workspace", "/media-workspace/new", "/content-studio", "/content-studio/new",
  "/voice-studio", "/voice-studio/new", "/video-studio", "/video-studio/new",
  "/subtitle-studio", "/subtitle-studio/new", "/image-studio", "/image-studio/new",
  "/document-workspace", "/document-workspace/new"]) {
  test("existing exact route still uses real project reader: " + route, async () => {
    const r = runtime({route, enabled: false}), task = r.dispatch();
    assert.equal(r.reads.length, 1);
    assert.equal(r.reads[0], route === "/projects"
      ? "/projects?limit=50&offset=200&q=OLD+CUSTOMER+QUERY&state=archived"
      : "/projects?limit=50&offset=0");
    r.pending[0].resolve(payload()); await task;
    assert.equal(r.state.projects[0].id, ID); assert.equal(r.state.projects[0].title, TITLE);
  });
}

for (const kind of ["epoch", "session", "route", "logout"]) {
  for (const outcome of ["success", "failure"]) {
    test(`actual reader discards ${outcome} after ${kind} changes`, async () => {
      const r = runtime(), task = r.read(), beforeMerges = r.merges.length;
      assert.deepEqual(r.reads, ["/projects?limit=50&offset=0"]);
      r.mutate(kind);
      if (outcome === "success") r.pending[0].resolve(payload());
      else r.pending[0].reject(Error("SYNTHETIC_TRANSPORT_FAILURE"));
      await task;
      assert.equal(r.merges.length, beforeMerges); assert.deepEqual(json(r.state.projects), []);
    });
  }
}

for (const response of [
  {ok: true, status: "guarded", data: {items: [item()]}},
  {ok: true, status: "read_only", data: {}},
  {ok: true, status: "read_only", data: {items: [{id: "invalid", title: TITLE, state: "active"}]}}
]) test("actual reader rejects invalid envelope or UUID without retaining old projects: " + JSON.stringify(response), async () => {
  const r = runtime(); r.state.projects = [item()];
  const task = r.read(); r.pending[0].resolve(response); await task;
  assert.equal(r.state.projectCenterReadState, "failed");
  assert.deepEqual(json(r.state.projects), []);
});

test("actual reader accepts an honest empty list", async () => {
  const r = runtime(), task = r.read(); r.pending[0].resolve(payload([])); await task;
  assert.equal(r.state.projectCenterReadState, "ready"); assert.deepEqual(json(r.state.projects), []);
});

test("actual reader preserves names and bounds overlong transport data without mutating input", async () => {
  const items = Array.from({length: 101}, (_, index) => ({...item(), title: TITLE + index}));
  const response = payload(items), snapshot = JSON.stringify(response);
  const r = runtime(), task = r.read(); r.pending[0].resolve(response); await task;
  assert.equal(r.state.projects.length, 100); assert.equal(r.state.projects[0].title, TITLE + "0");
  assert.equal(r.state.projects[99].title, TITLE + "99"); assert.equal(JSON.stringify(response), snapshot);
});
