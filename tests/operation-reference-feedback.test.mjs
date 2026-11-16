import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {operationReferenceFeedbackSources,operationReferenceFeedbackRuntime as runtime,REFERENCE_CUSTOMER,REFERENCE_IDS as ids} from "./helpers/operation-reference-feedback-runtime.mjs";
import {operationReferenceFeedbackHistoricalIntegrationSource as integrationBack,operationReferenceFeedbackHistoricalI18nSource as i18nBack,operationReferenceFeedbackHistoricalSnapshot as catalogBack} from "./helpers/operation-reference-feedback-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/operation-reference-feedback-reviewed.json",import.meta.url),"utf8"));
const source=operationReferenceFeedbackSources(),baseline=operationReferenceFeedbackSources(fixture.base),locales=["vi","en","zh"];
const routes=["/documents/split","/image/resize"],actions=["filter","clear","page"],suffixes=["failed","page","cleared","filtered"];
const text={
  vi:{failed:"Chưa tải được tệp. Hãy thử lại.",page:"Đã tải danh sách tệp.",cleared:"Đã xóa bộ lọc.",filtered:"Đã lọc danh sách tệp."},
  en:{failed:"Files could not be loaded. Please try again.",page:"File list loaded.",cleared:"Filter cleared.",filtered:"File list filtered."},
  zh:{failed:"无法加载文件。请重试。",page:"已加载文件列表。",cleared:"已清除筛选。",filtered:"已筛选文件列表。"}
};
const keyFor=action=>action==="filter"?"filtered":action==="clear"?"cleared":"page";
const plain=value=>JSON.parse(JSON.stringify(value)),hash=value=>createHash("sha256").update(value).digest("hex"),count=(value,part)=>value.split(part).length-1;
const freeze=value=>{if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
function once(value,old,next){assert.equal(count(value,old),1,"Exact reviewed slot must occur once");return value.replace(old,()=>next);}
function fieldsFor(route,action){
  const doc=route.startsWith("/documents/"),stem=doc?"__documentAssetReference":"__imageOperationAssetReference";
  return freeze({asset_reference_q:action==="clear"?"IGNORED CUSTOMER":"  CUSTOMER   Bot  PDF  ",[stem+"Offset"]:50,[stem+"Selections"]:[ids[0],ids[0],"BAD"]});
}
function references(r,route){return route.startsWith("/documents/")?r.state.documentAssetReferences:r.state.imageOperationAssetReferences;}
function readState(r,route){return r.state[route.startsWith("/documents/")?"documentAssetReferenceReadState":"imageOperationAssetReferenceReadState"];}
function checkRequest(r,route,action){
  assert.equal(r.pending.length,1);assert.equal(r.network.length,1);assert.equal(r.toasts.length,0,"No toast before the real GET settles");
  const expected={reference_kind:route.startsWith("/documents/")?"pdf":"image",limit:"50",offset:action==="page"?"50":"0"};
  if(action!=="clear")expected.q=action==="page"?"OLD CUSTOMER":"CUSTOMER Bot PDF";
  assert.deepEqual(r.network[0],{path:"/api/v1/asset-vault",method:"GET",query:expected});return expected;
}
function checkPinned(r,route){
  const refs=references(r,route),pins=route.startsWith("/documents/")?refs.pinned_pdf:refs.pinned;
  assert.deepEqual(plain(pins),[r.pinned,r.selected]);assert.ok(pins.every(item=>item.display_name===REFERENCE_CUSTOMER));
}
function payloadFor(r,query){
  const offset=Number(query.offset);
  return freeze({items:[r.received],has_more:true,next_offset:offset+50,filters:{q:query.q||"",reference_kind:query.reference_kind},
    pagination:{limit:50,offset,returned:1,has_more:true,next_offset:offset+50,previous_offset:offset>=50?offset-50:null}});
}
for(const locale of locales){
  test(`${locale}: six real reference actions await typed GET success/failure, preserve selected/pinned metadata and emit truthful copy`,async()=>{
    for(const route of routes)for(const action of actions)for(const failed of [false,true]){
      const r=runtime(locale,route,source),fields=fieldsFor(route,action),saved=JSON.stringify(fields),job=r.run(action,fields),query=checkRequest(r,route,action);
      const data=payloadFor(r,query),savedData=JSON.stringify(data);r.settle(0,{failed,data});await job;
      assert.equal(JSON.stringify(fields),saved);assert.equal(JSON.stringify(data),savedData);assert.equal(r.network.length,1);assert.equal(r.pending.length,1);
      assert.equal(r.toasts.length,1);assert.equal(r.toasts[0].textContent,text[locale][failed?"failed":keyFor(action)]);
      assert.equal(r.toasts[0].attributes.role,failed?"alert":"status");assert.equal(r.toasts[0].innerHTML,"");
      assert.equal(readState(r,route),failed?"failed":"ready");checkPinned(r,route);
      const refs=references(r,route),items=route.startsWith("/documents/")?refs.pdf:refs.items,listing=route.startsWith("/documents/")?refs.pdf_listing:refs.listing;
      assert.deepEqual(plain(items),failed?[]:[r.received]);assert.deepEqual(plain(listing.filters),{q:query.q||""});
      assert.deepEqual(plain(listing.pagination),{limit:50,offset:Number(query.offset),returned:failed?0:1,has_more:!failed,next_offset:failed?null:Number(query.offset)+50,previous_offset:action==="page"?0:null});
      if(failed)assert.equal(r.toasts.some(node=>node.attributes.role==="status"),false,"A failed GET cannot claim success");
    }
  });
  test(`${locale}: same-VM locale at settlement, missing translations and hostile values use the real plain-text toast`,async()=>{
    for(const route of routes){
      const next=locales[(locales.indexOf(locale)+1)%3],r=runtime(locale,route,source),job=r.run("filter",fieldsFor(route,"filter"));
      checkRequest(r,route,"filter");r.setLocale(next);r.settle(0);await job;assert.equal(r.toasts[0].textContent,text[next].filtered);
      for(const mode of ["missing","empty"]){
        const fallback=runtime(locale,route,source);fallback.translation(mode);const pending=fallback.run("clear",fieldsFor(route,"clear"));
        checkRequest(fallback,route,"clear");fallback.settle(0);await pending;assert.equal(fallback.toasts[0].textContent,"Đã xóa bộ lọc.");assert.equal(fallback.toasts[0].attributes.role,"status");
      }
      const hostile='<img src=x onerror="alert(1)"> \'&';
      for(const [action,failed]of [["filter",false],["clear",false],["page",false],["filter",true]]){
        const h=runtime(locale,route,source);h.translation("hostile",hostile);const pending=h.run(action,fieldsFor(route,action));checkRequest(h,route,action);
        h.settle(0,{failed});await pending;assert.equal(h.toasts[0].textContent,hostile,"textContent receives literal text, never escaped or parsed markup");
        assert.equal(h.toasts[0].innerHTML,"");assert.equal(h.toasts[0].attributes.role,failed?"alert":"status");checkPinned(h,route);
      }
    }
  });
  test(`${locale}: four frozen catalogue keys append exactly, retaining all prior entries and rejecting missing/unknown/partial groups`,()=>{
    const now=runtime(locale,routes[0],source),old=runtime(locale,routes[0],baseline);assert.ok(Object.isFrozen(now.messages[locale]));
    const entries=plain(Object.entries(now.messages[locale])),prior=plain(Object.entries(old.messages[locale])),added=suffixes.map(key=>["operationReferenceFeedback."+key,text[locale][key]]);
    assert.deepEqual(entries.slice(0,-4),prior);assert.deepEqual(entries.slice(-4),added);assert.deepEqual(catalogBack(entries,locale),prior);assert.deepEqual(catalogBack(prior,locale),prior);
    for(const [key]of added){
      assert.throws(()=>catalogBack(entries.filter(([name])=>name!==key),locale),/Unreviewed operation reference feedback/);
      assert.throws(()=>catalogBack(entries.map(([name,value])=>[name,name===key?"UNKNOWN":value]),locale),/Unreviewed operation reference feedback/);
    }
    assert.throws(()=>catalogBack([...entries,["operationReferenceFeedback.unknown","UNKNOWN"]],locale),/Unreviewed operation reference feedback/);
    assert.throws(()=>catalogBack([...entries,entries.at(-1)],locale),/Unreviewed operation reference feedback/);
    assert.throws(()=>catalogBack([...prior,...added.reverse()],locale),/Unreviewed operation reference feedback/);
    const outside=["customerOutside","CUSTOMER Bot <literal>"];assert.deepEqual(catalogBack([...prior,outside,...suffixes.map(key=>["operationReferenceFeedback."+key,text[locale][key]])],locale),[...prior,outside]);
  });
}
test("permission and unsupported-route guards remain exactly BASE behavior, outside the four-key copy contract",async()=>{
  for(const locale of locales)for(const route of routes)for(const guard of ["permission-false","permission-string","permission-undefined","unsupported-route"]){
    const now=runtime(locale,route,source),old=runtime(locale,route,baseline);
    if(guard.startsWith("permission"))for(const r of [now,old])r.mutate("permission",guard==="permission-false"?false:guard==="permission-string"?"true":undefined);
    const eventRoute=guard==="unsupported-route"?"/dashboard":route,fields=fieldsFor(route,"filter");
    await Promise.all([now.run("filter",fields,eventRoute),old.run("filter",fields,eventRoute)]);
    assert.equal(now.network.length,0);assert.equal(old.network.length,0);assert.equal(now.toasts.length,1);assert.equal(now.toasts[0].attributes.role,"alert");
    assert.deepEqual(now.observe(),old.observe(),"Do not expand the copy unit into guard-string changes");
  }
});
test("stale route/session/request/logout are BASE-characterization probes, not a new silence requirement",async t=>{
  const observations=[];
  for(const route of routes)for(const reason of ["route","session","request","logout"]){
    const now=runtime("vi",route,source),old=runtime("vi",route,baseline),fields=fieldsFor(route,"filter");
    const next=now.run("filter",fields),prior=old.run("filter",fields);checkRequest(now,route,"filter");checkRequest(old,route,"filter");
    now.mutate(reason);old.mutate(reason);now.settle(0);old.settle(0);await Promise.all([next,prior]);
    const a=now.observe(),b=old.observe();assert.deepEqual(a.network,b.network);assert.deepEqual(a.state,b.state);
    assert.deepEqual(a.toasts.map(value=>value.role),b.toasts.map(value=>value.role),"Preserve existing stale behavior; silence is not authorized by this copy contract");
    for(const toast of a.toasts){assert.equal(toast.role,"alert");assert.equal(toast.text,text.vi.failed);}
    observations.push({route,reason,baselineToasts:b.toasts,candidateToasts:a.toasts,classification:"BASELINE_CHARACTERIZATION_NOT_AGY_COPY_FAILURE"});
  }
  t.diagnostic(JSON.stringify({staleSilenceRequirement:"NOT_IN_COPY_CONTRACT",observations}));
});
test("six exact edits bind full raw integration/i18n and preserve portal/theme and every outside byte",()=>{
  assert.match(fixture.base,/^[a-f0-9]{40}$/);assert.equal(fixture.changes.length,6);
  const rebuilt={...baseline};
  for(const edit of fixture.changes){assert.equal(edit.count,1);const key=edit.file.endsWith("integration.js")?"integration":"i18n";rebuilt[key]=once(rebuilt[key],edit.old,edit.new);}
  assert.deepEqual(rebuilt,source);assert.equal(fixture.changes[1].new,fixture.changes[3].new);
  for(const [key,suffix,inverse]of [["integration","Integration",integrationBack],["i18n","I18n",i18nBack]]){
    assert.equal(hash(baseline[key]),fixture.binding["baseline"+suffix]);assert.equal(hash(source[key]),fixture.binding["candidate"+suffix]);
    assert.equal(inverse(source[key]),baseline[key]);assert.equal(inverse(baseline[key]),baseline[key]);
    const prefix='\r\n/* CUSTOMER prefix */\r\n',tail='\r\n/* CUSTOMER Bot Facebook TikTok suffix */\r\n';assert.equal(inverse(prefix+source[key]+tail),prefix+baseline[key]+tail);
  }
  for(const [key,suffix]of [["portal","Portal"],["theme","Theme"]]){assert.equal(source[key],baseline[key]);assert.equal(hash(source[key]),fixture.binding["candidate"+suffix]);}
});
test("owner-scoped inverse rejects partial, changed, duplicate and misplaced feedback without hiding unrelated bytes",()=>{
  for(const index of [0,2,4]){
    const edit=fixture.changes[index];assert.throws(()=>integrationBack(once(source.integration,edit.new,edit.old)),/Unreviewed operation reference feedback/);
    assert.throws(()=>integrationBack(source.integration+"\n"+edit.new),/Unreviewed operation reference feedback/);
  }
  const failed=fixture.changes[1].new;assert.equal(count(source.integration,failed),2);
  assert.throws(()=>integrationBack(source.integration.replace(failed,fixture.changes[1].old)),/Unreviewed operation reference feedback/);
  assert.throws(()=>integrationBack(source.integration.replace(failed,fixture.changes[1].old)+"\n"+failed),/Unreviewed operation reference feedback/);
  assert.throws(()=>integrationBack(source.integration.replace('operationReferenceFeedbackText("page"','operationReferenceFeedbackText("UNKNOWN"')),/Unreviewed operation reference feedback/);
  const edit=fixture.changes[5];assert.throws(()=>i18nBack(source.i18n+"\n"+edit.new),/Unreviewed operation reference feedback/);
  assert.throws(()=>i18nBack(once(source.i18n,edit.new,edit.new.replace("operationReferenceFeedback.failed","operationReferenceFeedback.UNKNOWN"))),/Unreviewed operation reference feedback/);
  const outside="/* CUSTOMER unrelated old source */\r\n";assert.equal(integrationBack(outside),outside);assert.equal(i18nBack(outside),outside);
});
// Full real integration executes only when root runs this suite. Native UI, provider output and LIVE are separate gates.
