import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {fileURLToPath} from "node:url";
import {createHash} from "node:crypto";
import {execFileSync} from "node:child_process";
import {fullBundleI18n} from "./helpers/feature-catalog-full-bundle135-render.mjs";

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const read=file=>fs.readFileSync(path.join(root,file),"utf8").replace(/\r\n/g,"\n");
const hash=value=>createHash("sha256").update(value).digest("hex");
const fixtureRaw=read("tests/fixtures/feature-family-native-chrome.json");
assert.equal(hash(fixtureRaw),"6da6b40e9a7a62b11363b3af067306e721fb51ddbdb6042b70ac5d601fc7cbff");
const fixture=JSON.parse(fixtureRaw),files=fixture.applicationSources.map(row=>row.file);
const physical=Object.fromEntries(files.map(file=>[file,read(file)]));
const before=Object.fromEntries(files.map(file=>[file,execFileSync("git",["show",fixture.base_sha+":"+file],
  {cwd:root,encoding:"utf8",maxBuffer:12e6}).replace(/\r\n/g,"\n")]));
const api=fullBundleI18n(physical["static/portal/portal-i18n.js"]);
const baseApi=fullBundleI18n(before["static/portal/portal-i18n.js"]);
const expectedCopy=new Map(fixture.copyRows.map(row=>[row.key,row]));
const entryFixtureRaw=read(fixture.protectedEntryFixture);
assert.equal(hash(entryFixtureRaw),fixture.protectedEntryFixtureLfSha256);
const canonical=JSON.parse(entryFixtureRaw).copy;
const entries=JSON.parse(read("tests/fixtures/feature-catalog-full-bundle135.json")).entries;
const esc=value=>String(value).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");
const families=["content","image","video","voice","music","subtitle","documents"];
const unit=entry=>({...entry,state:"guarded",engine:{mode:"guarded",execution_state:"guarded"},readiness:{status:"guarded"}});

async function renderer(sources){
  let helper=read("tests/helpers/publishing-child-render.mjs");
  const rootAnchor="const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');";
  assert.equal(helper.split(rootAnchor).length-1,1);helper=helper.replace(rootAnchor,"const root="+JSON.stringify(root)+";");
  for(const[name,file]of[["portal","static/portal/portal.js"],["i18n","static/portal/portal-i18n.js"]]){
    const anchor=`const ${name}=fs.readFileSync(path.join(root,'${file}'),'utf8');`;
    assert.equal(helper.split(anchor).length-1,1);helper=helper.replace(anchor,`const ${name}=${JSON.stringify(sources[file])};`);
  }
  const expose="normalizePublishReviewPackResult,customerMobileNavGroupForPath};";
  assert.equal(helper.split(expose).length-1,1);
  helper=helper.replace(expose,"normalizePublishReviewPackResult,customerMobileNavGroupForPath,renderFeatureFamily};");
  const result="return {html,text:plain(html),";assert.equal(helper.split(result).length-1,1);
  helper=helper.replace(result,'return {familyPreview:family=>window.__childLocale.renderFeatureFamily({path:"/features/"+family,featureFamily:family},context),html,text:plain(html),');
  return(await import("data:text/javascript;base64,"+Buffer.from(helper).toString("base64"))).renderChild;
}
// The current renderer is constructed from raw physical files, never an inverse.
const current=await renderer(physical),baseline=await renderer(before);
const controls=html=>[...html.matchAll(/<(?:a|button|input|form|select|textarea|option)\b[^>]*>/g)].map(row=>row[0]);
function reviewedText(html,locale){
  for(const row of fixture.copyRows)if(row.before[locale]!==row.after[locale]){
    html=html.replaceAll(esc(row.before[locale]),esc(row.after[locale]));
  }
  return html;
}
function expectedFamilyMarkup(html,locale,family){
  const marker='<section class="portal-feature-catalog">',start=html.indexOf(marker);assert(start>=0);
  const prefix=html.slice(0,start);let section=html.slice(start);
  const title=baseApi.t("featureCatalog.group."+family+".title",locale);
  const description=baseApi.t("featureCatalog.group."+family+".description",locale);
  const suffix=baseApi.t("featureCatalog.family.bodySuffix",locale);
  for(const owned of[
    '<span class="portal-section-kicker">'+esc(title)+'</span>',
    "<p>"+esc(description)+" "+esc(suffix)+"</p>"
  ]){
    assert.equal(section.split(owned).length-1,1,"Exactly one reviewed repeated node exists in BASE section");
    section=section.replace(owned,"");
  }
  return reviewedText(prefix+section,locale);
}
for(const locale of["vi","en","zh"]){
  for(const row of fixture.copyRows)test(`raw full dictionary uses reviewed family copy: ${locale}.${row.key}`,()=>{
    assert.equal(api.t(row.key,locale),row.after[locale]);
  });
  for(const family of families)for(const mode of["filled","empty"])test(`actual family preserves useful output and outside markup: ${locale}.${family}.${mode}`,()=>{
    const catalog=mode==="filled"?entries.map(unit):[unit(entries.find(row=>row.group!==family))];
    const raw={catalog,profile:{locale,displayName:"CUSTOMER studio <script> & media"}},saved=JSON.stringify(raw);
    const value=current(locale,"/features/"+family,raw),old=baseline(locale,"/features/"+family,structuredClone(raw));
    assert.equal(JSON.stringify(raw),saved);assert.equal(JSON.stringify(value.context),JSON.stringify(old.context));
    assert.deepEqual(controls(value.html),controls(old.html),"Routes, form/control attributes and native permissions remain unchanged");
    assert.equal(value.html,expectedFamilyMarkup(old.html,locale,family),"No other markup or customer data may change");
    const at=value.html.indexOf('<section class="portal-feature-catalog">'),section=value.html.slice(at);
    const heading=section.slice(0,section.indexOf("</div>")+6);
    assert.doesNotMatch(heading,/portal-section-kicker|<p>/);assert.match(heading,/<h2>/);
    const key="featureCatalog.group."+family+".description";
    const description=expectedCopy.get(key)?.after[locale]||baseApi.t(key,locale);
    assert.equal(value.html.split(esc(description)).length-1,1,"The group description remains once in the actual hero");
    assert(value.html.includes('href="/features"'));assert.doesNotMatch(value.html,/<script> & media/);
    if(mode==="empty"){
      assert.doesNotMatch(section,/class="portal-module-card\b/);
      for(const key of["featureCatalog.family.emptyTitle","featureCatalog.family.emptyBody"]){
        assert(section.includes(esc(expectedCopy.get(key).after[locale])));
      }
    }else assert.match(section,/class="portal-module-card\b/);
  });
  test(`unknown family retains actual not-found output except reviewed title: ${locale}`,()=>{
    const now=current(locale,"/features/image",{}).familyPreview("owner_unknown");
    const old=baseline(locale,"/features/image",{}).familyPreview("owner_unknown");
    assert.equal(now,reviewedText(old,locale));assert.deepEqual(controls(now),controls(old));
    assert.doesNotMatch(now,/class="portal-module-card\b/);
  });
  test(`every other fixed message and all270 catalogue entry fields remain held: ${locale}`,()=>{
    const owned=new Set(fixture.copyRows.map(row=>row.key));
    const plain=value=>JSON.parse(JSON.stringify(value));
    assert.deepEqual(plain(Object.fromEntries(Object.entries(api.messages[locale]).filter(([key])=>!owned.has(key)))),
      plain(Object.fromEntries(Object.entries(baseApi.messages[locale]).filter(([key])=>!owned.has(key)))));
    for(const[key,row]of Object.entries(canonical[locale]))for(const field of["title","description"]){
      assert.equal(api.t(`featureCatalog.entry.${key}.${field}`,locale),row[field]);
    }
  });
}
for(const pin of fixture.applicationSources)test(`raw application is exactly BASE plus accepted worker records: ${pin.file}`,()=>{
  let candidate=before[pin.file];assert.equal(hash(candidate),pin.beforeLfSha256);
  for(const row of fixture.records.filter(row=>row.file===pin.file)){
    assert.equal(candidate.split(row.old).length-1,1);candidate=candidate.replace(row.old,()=>row.new);
  }
  assert.equal(hash(candidate),pin.afterLfSha256);assert.equal(hash(physical[pin.file]),pin.afterLfSha256);
  assert.equal(physical[pin.file],candidate);
});
test("only20 reviewed fixed values change and the already-correct Vietnamese music title remains literal",()=>{
  let changed=0;
  for(const row of fixture.copyRows)for(const locale of["vi","en","zh"]){
    assert.equal(baseApi.t(row.key,locale),row.before[locale]);if(row.before[locale]!==row.after[locale])changed++;
  }
  assert.equal(changed,20);assert.equal(fixture.records.length,21);assert.equal(fixture.held.length,1);
  const held=fixture.held[0];assert.equal(api.t(held.key,held.locale),held.value);
});
