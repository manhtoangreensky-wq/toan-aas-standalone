import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import test from "node:test";
import {createHash} from "node:crypto";
import {fileURLToPath} from "node:url";

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const rawFixture=fs.readFileSync(path.join(root,"tests/fixtures/feature-catalog-descriptions108.json"),"utf8").replace(/\r\n/g,"\n");
assert.equal(createHash("sha256").update(rawFixture).digest("hex"),"0decec95d52d462c18482c823cb7032d8c4f5815cbc78516659f86036430f294");
const fixture=JSON.parse(rawFixture);
// Newest acceptance always reads physical bytes, never a historical projection.
const copySource=fs.readFileSync(path.join(root,fixture.applicationFile),"utf8").replace(/\r\n/g,"\n");
const renderer=fs.readFileSync(path.join(root,"static/portal/portal-features.js"),"utf8");
class Element {
  constructor(tag){this.tagName=tag.toUpperCase();this.className="";this.textContent="";this.children=[];this.attributes={};}
  setAttribute(name,value){this.attributes[name]=String(value);}
  appendChild(child){this.children.push(child);return child;}
}
const document={createElement:tag=>new Element(tag)},window={};
const context=vm.createContext({window,document,console,Set,Object,Array});
vm.runInContext(copySource,context);
const boot="window.__TOAN_AAS_FEATURES_READY__ = hydrateFeatures();";
assert.equal(renderer.split(boot).length-1,1);
vm.runInContext(renderer.replace(boot,"window.__descriptionCopyTest = { featureCard, COPY };"),context);
const{featureCard,COPY}=window.__descriptionCopyTest,dictionary=window.TOANAASFeatureCatalogCopy;
const collect=node=>[node,...node.children.flatMap(collect)];
const states=[["guarded","guarded"],["web_native","planning_only"],["bot_companion","available"]];

for(const locale of["vi","en","zh"])for(const entry of fixture.entries){
  test(`customer description preserves title/route/search/state/input: ${locale}.${entry.key}`,()=>{
    const expected=fixture.copy[locale][entry.key];
    for(const[mode,status]of states){
      const input={key:entry.key,route:entry.route,group:entry.group,kind:"customer",
        title:entry.sourceTitle,description:entry.sourceDescription,
        engine:{mode,execution_state:mode==="guarded"?"guarded":"ready"},readiness:{status}};
      const before=JSON.stringify(input),card=featureCard(input,COPY[locale],locale),nodes=collect(card);
      assert.equal(nodes.find(node=>node.tagName==="H3").textContent,expected.title);
      assert.equal(nodes.find(node=>node.tagName==="P").textContent,expected.description);
      assert.equal(nodes.find(node=>node.tagName==="A").attributes.href,entry.route);
      assert.equal(card.attributes["data-feature-key"],entry.key);
      assert.equal(card.attributes["data-feature-route"],entry.route);
      assert.equal(nodes.find(node=>node.className==="portal-engine-label").attributes["data-engine-mode"],mode);
      assert.equal(nodes.find(node=>node.className==="portal-readiness-label").attributes["data-readiness"],status);
      for(const term of[expected.title,expected.description,input.title,input.description,entry.key,entry.route]){
        if(term)assert(card.attributes["data-catalog-text"].includes(term.toLocaleLowerCase()));
      }
      assert.equal(JSON.stringify(input),before);
    }
  });
}
for(const locale of["vi","en","zh"])test(`unregistered copy remains literal source text in ${locale}`,()=>{
  const input={key:"future_unregistered_tool",route:"/future-tool",group:"other",kind:"customer",
    title:"Owner title <safe>",description:"Owner description <script> & details",engine:{mode:"guarded"},readiness:{status:"guarded"}};
  const before=JSON.stringify(input),nodes=collect(featureCard(input,COPY[locale],locale));
  assert.equal(nodes.find(node=>node.tagName==="H3").textContent,input.title);
  assert.equal(nodes.find(node=>node.tagName==="P").textContent,input.description);
  assert.equal(JSON.stringify(input),before);
});
test("all135 titles,27 Video rows and exactly324 reviewed description values retain the closed inventory",()=>{
  const target=new Set(fixture.entries.map(row=>row.key));
  assert.equal(target.size,108);assert.equal(fixture.records.length,322);assert.equal(fixture.heldValues,2);
  let held=0;
  for(const locale of["vi","en","zh"]){
    assert.equal(Object.keys(dictionary[locale]).length,135);
    assert.deepEqual(Object.keys(dictionary[locale]).sort(),Object.keys(fixture.beforeCopy[locale]).sort());
    for(const[key,row]of Object.entries(fixture.beforeCopy[locale])){
      assert.equal(dictionary[locale][key].title,row.title);
      if(!target.has(key))assert.deepEqual(JSON.parse(JSON.stringify(dictionary[locale][key])),row);
      else if(fixture.copy[locale][key].description===row.description)held++;
    }
  }
  assert.equal(held,2);
});
test("physical current source equals the independently frozen reviewed candidate",()=>{
  assert.equal(createHash("sha256").update(copySource).digest("hex"),fixture.afterLfSha256);
});
