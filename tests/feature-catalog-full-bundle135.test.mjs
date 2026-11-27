import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {fileURLToPath} from "node:url";
import {createHash} from "node:crypto";
import {execFileSync} from "node:child_process";
import {fullBundleI18n,fullBundleConsumer,cardText} from "./helpers/feature-catalog-full-bundle135-render.mjs";
import {featureFamilyNativeChromeHistoricalSource} from "./helpers/feature-family-native-chrome-historical.mjs";
import {galleryCustomerCopyHistoricalSource} from "./helpers/gallery-customer-copy-historical.mjs";

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const read=file=>fs.readFileSync(path.join(root,file),"utf8").replace(/\r\n/g,"\n");
const hash=text=>createHash("sha256").update(text).digest("hex");
const rawFixture=read("tests/fixtures/feature-catalog-full-bundle135.json");
assert.equal(hash(rawFixture),"bcde5343c0494c81f7deefeb9fcae35293f2ecee4e35e4a35ff4d84ae0f08d28");
const fixture=JSON.parse(rawFixture),canonicalRaw=read(fixture.canonicalFixture);
assert.equal(hash(canonicalRaw),fixture.canonicalFixtureLfSha256);
const canonical=JSON.parse(canonicalRaw).copy;
// Historical FBC retains its epoch; newest Gallery acceptance reads raw physical.
const source=featureFamilyNativeChromeHistoricalSource(galleryCustomerCopyHistoricalSource(read(fixture.applicationFile),fixture.applicationFile),fixture.applicationFile),portal=read("static/portal/portal.js");
const before=execFileSync("git",["show",fixture.base_sha+":"+fixture.applicationFile],{cwd:root,encoding:"utf8",maxBuffer:10e6}).replace(/\r\n/g,"\n");
const api=fullBundleI18n(source),baseApi=fullBundleI18n(before);
const{render,manifest}=fullBundleConsumer(portal,api,fixture.entries);
const states=[["guarded","guarded"],["web_native","planning_only"],["bot_companion","available"]];

for(const locale of["vi","en","zh"])for(const entry of fixture.entries){
  test(`full dictionary and actual moduleCard use canonical copy: ${locale}.${entry.key}`,()=>{
    api.setLocale(locale,{emit:false});baseApi.setLocale(locale,{emit:false});
    const expected=canonical[locale][entry.key];
    assert.equal(api.t(`featureCatalog.entry.${entry.key}.title`),expected.title);
    assert.equal(api.t(`featureCatalog.entry.${entry.key}.description`),expected.description);
    const visible=entry.key==="workspace_menu"?{
      title:baseApi.t("page.workspaceMenu.title"),description:baseApi.t("page.workspaceMenu.description")
    }:expected;
    for(const[mode,status]of states){
      const input={...entry,title:"Owner module title",description:"Owner module description",state:"guarded",
        icon:"◩",engine:{mode,execution_state:mode==="guarded"?"guarded":"ready"},readiness:{status}};
      const saved=JSON.stringify(input),context={title:"Owner context title"};
      const html=render(input,context,"",{showEngineLabel:true});
      assert.equal(cardText(html,"h3"),visible.title);assert.equal(cardText(html,"p"),visible.description);
      assert(html.includes(`href="${entry.route}"`));
      assert(html.includes(`data-engine-mode="${mode}"`)&&html.includes(`data-readiness="${status}"`));
      assert.equal(JSON.stringify(input),saved);assert.equal(context.title,"Owner context title");
      assert(html.includes('<svg class="portal-icon"'),"real SVG helper must not be replaced with an empty icon");
    }
  });
}
for(const locale of["vi","en","zh"])test(`non-catalog mode and unknown owned fallback remain literal: ${locale}`,()=>{
  api.setLocale(locale,{emit:false});
  const entry=fixture.entries[0],input={...entry,title:"Owner <title>",description:"Owner <script> & description",state:"guarded"};
  const plain=render(input,{},"",{showEngineLabel:false});
  assert.equal(cardText(plain,"h3"),input.title);assert.equal(cardText(plain,"p"),input.description);
  assert.doesNotMatch(plain,/<script>/);
  const route="/owner-future",unknown={key:"future_owner_tool",route,state:"guarded",title:"Source title",description:"Source description"};
  manifest[route]={path:route,routePath:route,title:"Owner page <title>",description:"Owner page <script> & description",status:"guarded"};
  const html=render(unknown,{title:"Owner <context>"},"",{showEngineLabel:true});
  assert.equal(cardText(html,"h3"),"Owner <context>");
  assert.equal(cardText(html,"p"),manifest[route].description);assert.doesNotMatch(html,/<script>/);
  assert.equal(api.t("featureCatalog.entry.future_owner_tool.title"),"");
});
test("unsafe routes remain rejected without rendering a card",()=>{
  for(const route of["javascript:alert(1)","//outside.invalid/path","/bad\\path","/bad\u0000path"]){
    assert.equal(render({key:"dashboard",route,state:"guarded"},{},"",{showEngineLabel:true}),"");
  }
});
test("only270 owned fields per locale change; all other fixed messages and existing290values remain held",()=>{
  let held=0;
  assert.equal(fixture.keys.length,135);assert.equal(fixture.missingKeys.length,39);assert.equal(fixture.changedExisting.length,286);
  for(const locale of["vi","en","zh"]){
    const actual=api.messages[locale],prior=baseApi.messages[locale],prefix="featureCatalog.entry.";
    const owned=Object.keys(actual).filter(key=>key.startsWith(prefix));
    assert.equal(owned.length,270);
    assert.deepEqual(owned.sort(),fixture.keys.flatMap(key=>[prefix+key+".title",prefix+key+".description"]).sort());
    const plain=object=>JSON.parse(JSON.stringify(object));
    assert.deepEqual(plain(Object.fromEntries(Object.entries(actual).filter(([key])=>!key.startsWith(prefix)))),
      plain(Object.fromEntries(Object.entries(prior).filter(([key])=>!key.startsWith(prefix)))));
    for(const key of owned)if(Object.hasOwn(prior,key)&&prior[key]===actual[key])held++;
  }
  assert.equal(held,290);
});
test("historical FBC i18n source is the independently frozen candidate after finite FCH projection",()=>{
  assert.equal(hash(source),fixture.afterLfSha256);
});
