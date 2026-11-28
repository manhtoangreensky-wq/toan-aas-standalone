import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import {execFileSync} from "node:child_process";
import {fileURLToPath} from "node:url";
import {webcrypto} from "node:crypto";
import {customerNaturalHistoricalSnapshot} from "./helpers/customer-natural-followup-historical.mjs";

// Catches leaked implementation wording while preserving the actual controls,
// authored text, input rules and machine values in the document preparation UI.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const BASE = "cf94b23e6a26010e88ebcd33b36623204c784c9a";
const files = ["static/portal/portal-i18n.js", "static/portal/portal.js", "static/portal/integration.js"];
const current = Object.fromEntries(files.map(f => [f, fs.readFileSync(path.join(ROOT, f), "utf8")]));
const historical = Object.fromEntries(files.map(f => [f, execFileSync("git", ["show", BASE + ":" + f], {cwd: ROOT, encoding: "utf8", maxBuffer: 30e6})]));
const IDS = ["11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", "33333333-3333-4333-8333-333333333333"];
const CUSTOMER = 'Khách ghi QA metadata studio <img src=x onerror="1"> Facebook TikTok';
const json = value => JSON.parse(JSON.stringify(value));
const escape = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
const plain = html => String(html).replace(/<svg\b[\s\S]*?<\/svg>/g, " ").replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
const technical = /\b(?:QA|CSRF|UUID|API|metadata|workspace|brief|processing plan|self-review|guarded|canonical|provider|backend|frontend|runtime|revision|idempotency|owner-scoped|signed session|signed account|blob|fallback|web-native|feature flag|job|token)\b/i;
const viLeaks = /\b(?:plan|plans|review|tags?|source|refs?|archive|draft|server|browser|intent|planned|checklist|output|delivery|history|version|input|scan|text|document|tool|convert|engine|web-owned|scope|signed|processing|target format)\b/i;
function runtime(locale, route, sources = current, transport = null) {
  const noop = () => {}, network = [];
  const document = {readyState: "loading", visibilityState: "visible", addEventListener: noop,
    querySelector: () => null, querySelectorAll: () => [], getElementById: () => null,
    documentElement: {lang: locale, setAttribute: noop, getAttribute: () => null, classList: {add: noop, remove: noop}},
    body: {classList: {add: noop, remove: noop, toggle: noop}, setAttribute: noop}};
  const window = {document, navigator: {language: locale, userAgent: "Document wording check"},
    location: {pathname: route, search: "", href: "https://unit.invalid" + route, origin: "https://unit.invalid"},
    addEventListener: noop, dispatchEvent: noop, CustomEvent: function () {},
    matchMedia: () => ({matches: false, addEventListener: noop}),
    setTimeout: () => 0, clearTimeout: noop, crypto: webcrypto,
    localStorage: {getItem: () => null}, sessionStorage: {getItem: () => null}};
  window.__TOAN_AAS_PORTAL__ = {path:route,session:{authenticated:true,csrfToken:"synthetic-only"}};
  const fetch = (url,options) => {network.push({url,method:options.method,body:JSON.parse(options.body)});
    if(transport)return Promise.resolve(transport(url,options));
    throw Error("No network permitted");};
  const box = vm.createContext({window, document, navigator: window.navigator, URL, URLSearchParams,
    Headers, FormData, Blob, AbortController, Intl, console, fetch, crypto:webcrypto,setTimeout: () => 0, clearTimeout: noop});
  vm.runInContext(sources[files[0]], box);
  window.TOANAASI18n.setLocale(locale, {emit: false});
  const anchor = "  window.TOANAASPortal = Object.freeze({";
  const names = ["renderPage", "normalizeBootstrap", "documentTitle", "documentWorkspaceFields", "documentPlanFields",
    "documentWorkspaceEventLabel", "documentWorkspaceTypeLabel", "documentWorkspaceOperationLabel"];
  assert.equal(sources[files[1]].split(anchor).length - 1, 1);
  vm.runInContext(sources[files[1]].replace(anchor, "  window.__docCopy={" + names.join(",") + "};\n" + anchor), box);
  const integrationAnchor = '  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startInitialHydration, { once: true });';
  assert.equal(sources[files[2]].split(integrationAnchor).length - 1, 1);
  vm.runInContext(sources[files[2]].replace(integrationAnchor,
    "  window.__docFeedback={documentWorkspacePayload,documentPlanPayload,documentWorkspaceSafetyError,documentWorkspaceTags,documentWorkspaceFilterPayload,documentWorkspaceMutation};\n" + integrationAnchor), box);
  return {window, network, render(raw) {
    const snapshot = JSON.stringify(raw), p = window.__docCopy, page = window.TOANAASPortal.resolvePage(route);
    const context = p.normalizeBootstrap({path: route, interfaceLocale: locale,
      profile: {locale, displayName: "Người dùng"}, session: {authenticated: true, csrfToken: "synthetic-only"}, ...raw});
    const html = p.renderPage(page, context);
    assert.equal(JSON.stringify(raw), snapshot, "Customer data must not mutate");
    return {html, context: json(context), title: p.documentTitle(page, context)};
  }};
}
function data(state = "draft", {guard = false, empty = false, missing = false} = {}) {
  const workspace = {id: IDS[0], title: CUSTOMER, document_type: "pdf", language: "vi", target_language: "en",
    lifecycle: state, state, revision: 2, source_summary: CUSTOMER, objective: CUSTOMER, tags: [CUSTOMER], plan_count: 1};
  const plan = {id: IDS[1], workspace_id: IDS[0], title: CUSTOMER, operation: "split", instructions: CUSTOMER,
    state: "active", revision: 2, source_asset_id: IDS[2], reference_asset_id: "",
    tags: [CUSTOMER], versions: [{revision: 1, instructions_excerpt: CUSTOMER}]};
  const operations = ["organize","split","merge","optimize","image_to_pdf","pdf_to_images","pdf_to_word","ocr","translate","convert","other"];
  const routes = {split:"/documents/split",merge:"/documents/merge",optimize:"/documents/compress",
    image_to_pdf:"/documents/image-to-pdf",pdf_to_images:"/documents/pdf-to-images",pdf_to_word:"/documents/pdf-to-word"};
  return {documentWorkspaceEnabled: true, documentWorkspaceReadState: "ready",
    capabilities: Object.fromEntries(["view","create","filter","update","lifecycle","restore-version"]
      .map(x => ["document-workspace-" + x, !guard]).concat(["create","update","archive","restore","reorder","restore-version"].map(x => ["document-plan-" + x, !guard]))),
    documentWorkspaces: empty ? [] : [workspace],
    documentWorkspaceSummary: {workspaces: {total: empty ? 0 : 1, review: 0, approved: 0}},
    documentWorkspaceListing: {filters: {q:"", state:"active"}, pagination: {total: 1, offset: 0, limit: 50}},
    documentWorkspaceReferences: {projects: [{id: IDS[1], title: CUSTOMER}], document_assets: [{id: IDS[2], display_name: CUSTOMER, extension:"pdf"}]},
    documentWorkspacePolicy: {handoff_catalog: operations.map(operation => ({operation,
      availability: routes[operation] ? "available" : "guarded", route: routes[operation] || null,
      title: "Internal " + operation, summary: "Internal metadata workspace scope"}))},
    documentWorkspaceDetail: missing ? {} : {workspace, plans: [plan],
      versions: [{...workspace, revision:1}], events: [{action:"workspace_created",revision:1,created_at:"2026-11-28"}]},
    documentWorkspaceEvents: [{action:"workspace_created",revision:1,created_at:"2026-11-28"}]};
}
const controls = html => [...html.matchAll(/<(?:form|button|input|textarea|select|option|a)\b[^>]*>/g)]
  .map(m => m[0].replace(/\b(?:placeholder|aria-label|title|data-portal-confirm)="[^"]*"/g, 'copy="__text__"'));
function assertNatural(text, locale) {
  assert.equal(text.match(technical)?.[0] ?? null, null, "Implementation details must not reach customer wording");
  if (locale === "vi") assert.equal(text.match(viLeaks)?.[0] ?? null, null, "Vietnamese fixed wording must not mix English common words");
  if (locale === "en") assert.equal(text.match(/[À-ỹĐđ]|\p{Script=Han}/u)?.[0] ?? null, null, "English fixed wording must not mix Vietnamese or Chinese");
  if (locale === "zh") assert.match(text, /\p{Script=Han}/u);
}
for (const locale of ["vi","en","zh"]) {
  for (const [name, route, raw] of [
    ["list","/document-workspace",data()],
    ["new-empty","/document-workspace/new",data("draft",{empty:true})],
    ["access","/document-workspace",data("draft",{guard:true})],
    ["missing","/document-workspace/"+IDS[0],data("draft",{missing:true})],
    ...["draft","review","approved","archived"].map(state => [state,"/document-workspace/"+IDS[0],data(state)])
  ]) {
    test(`${locale}/${name}: real page uses natural wording without changing customer content or controls`, () => {
      const nowApp=runtime(locale,route), oldApp=runtime(locale,route,historical);
      const now=nowApp.render(raw), old=oldApp.render(structuredClone(raw));
      assert.deepEqual(now.context,old.context);
      assert.deepEqual(controls(now.html),controls(old.html),"Form identities, values, routes and permissions stay exact");
      const customer=escape(CUSTOMER), fixed=now.html.split(customer).join("CUSTOMER");
      assertNatural(plain(fixed)+" "+[...fixed.matchAll(/\b(?:placeholder|aria-label|title|data-portal-confirm)="([^"]*)"/g)].map(m=>m[1]).join(" "),locale);
      assert.ok(!now.html.includes("<img src=x"));
      if(old.html.includes(customer)) assert.ok(now.html.includes(customer),"Original customer wording must remain");
      assert.deepEqual(nowApp.network,[]);
    });
  }
  test(`${locale}: actual validators retain acceptance and return ordinary guidance`, () => {
    const now=runtime(locale,"/document-workspace"), old=runtime(locale,"/document-workspace",historical);
    const fields={title:"Yêu cầu tháng mười một",document_type:"pdf",source_summary:"Nội dung tài liệu",objective:"Tách trang đầu",language:"vi",target_language:"en",tags:"Hợp đồng, Facebook",project_id:IDS[1]};
    assert.deepEqual(json(now.window.__docFeedback.documentWorkspacePayload(fields)),json(old.window.__docFeedback.documentWorkspacePayload(fields)));
    const vectors=[
      ["documentWorkspacePayload",{...fields,title:"x"}],
      ["documentWorkspacePayload",{...fields,objective:""}],
      ["documentWorkspacePayload",{...fields,project_id:"invalid"}],
      ["documentWorkspacePayload",{...fields,tags:Array.from({length:21},(_,i)=>"Nhãn"+i)}],
      ["documentWorkspaceFilterPayload",{q:"",state:"invalid"}],
      ["documentPlanPayload",{title:"Bước xử lý",operation:"split",instructions:"",source_asset_id:IDS[2],reference_asset_id:IDS[2]}]
    ];
    for(const [name,input] of vectors){
      let a,b;try{now.window.__docFeedback[name](input);}catch(e){a=e.message;}
      try{old.window.__docFeedback[name](input);}catch(e){b=e.message;}
      assert.ok(a&&b,"Same invalid input must remain rejected");
      assertNatural(a,locale);
    }
    assert.deepEqual(now.network,[]);
  });
  test(`${locale}: fixed success wording is natural while the actual reply and request remain unchanged`, async () => {
    const receipt={ok:true,status:"completed",message:"Document brief metadata revision saved",data:{workspace:{id:IDS[0],revision:2}}};
    const snapshot=JSON.stringify(receipt);
    const app=runtime(locale,"/document-workspace",current,()=>({ok:true,status:200,json:async()=>receipt}));
    let display;
    const actual=await app.window.__docFeedback.documentWorkspaceMutation({action:"document-workspace-create",
      route:"/document-workspace",scope:"document-copy-create",path:"/document-workspace/workspaces",
      payload:{title:"Yêu cầu của tôi"},onSuccess:async reply=>{display=reply;}});
    assert.equal(JSON.stringify(receipt),snapshot,"The transport reply remains untouched");
    assert.equal(actual,receipt,"The original result object is returned");
    assert.deepEqual(json(actual),receipt,"The caller still receives its actual original reply");
    assert.equal(display.data,receipt.data,"The presentation copy preserves the original data reference");
    assert.deepEqual(json(display.data),receipt.data,"Only the displayed message can change");
    assertNatural(display.message,locale);
    assert.equal(app.network.length,1);assert.equal(app.network[0].method,"POST");
    assert.equal(app.network[0].url,"/api/v1/document-workspace/workspaces");
    assert.equal(app.network[0].body.title,"Yêu cầu của tôi");
    assert.equal(typeof app.network[0].body.idempotency_key,"string");
  });
  test(`${locale}: server rejection keeps status and details but shows an ordinary retry instruction`, async () => {
    const payload={ok:false,status:"guarded",message:"Workspace metadata revision conflict",error_code:"WEB_DOCUMENT_WORKSPACE_REVISION_CONFLICT",data:{}};
    const snapshot=JSON.stringify(payload);
    const app=runtime(locale,"/document-workspace",current,()=>({ok:false,status:409,json:async()=>payload}));
    let error,called=false;
    try{await app.window.__docFeedback.documentWorkspaceMutation({action:"document-workspace-update",
      route:"/document-workspace",scope:"document-copy-update",path:"/document-workspace/workspaces/"+IDS[0],
      payload:{title:"Yêu cầu của tôi",expected_revision:1},onSuccess:async()=>{called=true;}});}catch(e){error=e;}
    assert.ok(error);assert.equal(error.status,409);assert.deepEqual(json(error.payload),payload);
    assert.equal(error.payload,payload,"The original rejection details remain attached");
    assert.equal(JSON.stringify(payload),snapshot);assert.equal(called,false);
    assertNatural(error.message,locale);assert.equal(app.network.length,1);
  });
}
test("new document dictionary values are complete; every previous key and value stays exact", () => {
  const raw=runtime("vi","/document-workspace").window.TOANAASI18n.messages;
  // Only this older value comparator sees its original dictionary epoch.
  const now=Object.fromEntries(["vi","en","zh"].map(locale=>[locale,
    Object.fromEntries(customerNaturalHistoricalSnapshot(Object.entries(raw[locale]),locale))]));
  const old=runtime("vi","/document-workspace",historical).window.TOANAASI18n.messages;
  for(const locale of ["vi","en","zh"]) {
    for(const [key,value] of Object.entries(old[locale])) assert.equal(now[locale][key],value,key);
    const added=Object.keys(now[locale]).filter(key=>!Object.hasOwn(old[locale],key));
    assert.ok(added.length>0);assert.ok(added.every(key=>/^docPlain(?:Form|Detail|Feedback|Read)\./.test(key)));
    for(const key of added)for(const language of ["vi","en","zh"]) assert.equal(typeof now[language][key],"string",key);
  }
});
