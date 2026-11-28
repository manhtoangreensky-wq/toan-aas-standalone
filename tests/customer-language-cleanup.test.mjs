import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {execFileSync} from "node:child_process";
import {fileURLToPath} from "node:url";
import {renderChild as current} from "./helpers/publishing-child-render.mjs";
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const BASE="2817dd9d221e04aa45945165ae60d5838cf9d920";
let helper=fs.readFileSync(path.join(ROOT,"tests/helpers/publishing-child-render.mjs"),"utf8");
const replacements=[["const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');","const root="+JSON.stringify(ROOT)+";"]];
for(const[name,file]of [["portal","static/portal/portal.js"],["i18n","static/portal/portal-i18n.js"]])
  replacements.push([`const ${name}=fs.readFileSync(path.join(root,'${file}'),'utf8');`,
    "const "+name+"="+JSON.stringify(execFileSync("git",["show",BASE+":"+file],{cwd:ROOT,encoding:"utf8",maxBuffer:30e6}))+";"]);
for(const[before,after]of replacements){assert.equal(helper.split(before).length-1,1);helper=helper.replace(before,()=>after);}
const {renderChild:old}=await import("data:text/javascript;base64,"+Buffer.from(helper).toString("base64"));
const CUSTOMER="Khách ghi QA metadata Studio Facebook TikTok <img src=x onerror=1>";
const escaped=value=>value.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
const text=html=>html.split(escaped(CUSTOMER)).join("CUSTOMER").replace(/<svg\b[\s\S]*?<\/svg>/g," ").replace(/<[^>]*>/g," ").replace(/\s+/g," ");
const controls=html=>[...html.matchAll(/<(?:a|button|form|input|select|textarea|option)\b[^>]*>/g)].map(row=>row[0].replace(/\btitle="[^"]*"/g,'title="COPY"'));
const cases=[
 {name:"account-unlinked",route:"/account",raw:{}},
 {name:"account-linked",route:"/account",raw:{linkStatus:{linked:true},profile:{accountType:"telegram",loginMethods:{telegram:true}}}},
 {name:"setup",route:"/workspace/setup",raw:{capabilities:{"workspace-setup-save":true},workspaceSetup:{readState:"read_only",profile:{setup_state:"not_started",revision:0,focus_areas:[]}}}},
 ...["vi","en","zh"].map(selected=>({name:"language-"+selected,route:"/account/interface-language",raw:{profile:{locale:selected},capabilities:{"update-profile":true}}})),
 {name:"language-guarded",route:"/account/interface-language",raw:{profile:{locale:"vi"},capabilities:{}}}
];
const technical=/\b(?:Web|QA|metadata|catalogue|catalog|CSRF|signed session|reviewed|review|preference|coverage|fallback|state transfer|workflow|provider|backend|frontend)\b|目录|偏好边界|会话|Công bố phạm vi|Ranh giới/i;
for(const locale of ["vi","en","zh"])for(const item of cases)test(`${locale}/${item.name}: ordinary words, same real controls and data`,()=>{
 const raw={...structuredClone(item.raw),profile:{locale,displayName:CUSTOMER,...structuredClone(item.raw.profile||{})}};
 const previous=old(locale,item.route,structuredClone(raw)),next=current(locale,item.route,structuredClone(raw));
 assert.equal(JSON.stringify(next.context),JSON.stringify(previous.context));
 assert.deepEqual(controls(next.html),controls(previous.html),"No field, action, value, permission, selected state or destination change");
 assert(!next.html.includes("<img src=x"));
 if(previous.html.includes(escaped(CUSTOMER)))assert(next.html.includes(escaped(CUSTOMER)));
 if(item.route==="/account"){
   const quick=next.html.match(/<section class="portal-account-command"[\s\S]*?<\/section>/)?.[0];assert(quick);
   assert(!/\bWeb\b|\bSession\b|\bPhiên\b|会话/i.test(text(quick)),"Quick facts must use ordinary account wording");
   const metadata=next.html.match(/<div class="portal-summary-list">([\s\S]*?)<\/div>/)?.[0];
   assert(!next.html.includes(next.messages[locale]["accountCenter.profile.profileDefaultsLabel"]+"</span>"),
     "Do not display a non-actionable language/timezone/avatar code summary");
   assert(next.html.includes('name="locale"')&&next.html.includes('name="timezone"'),"Profile fields remain available");
   assert(!/\bWeb\b/.test(next.messages[locale]["page.account.description"]));
   void metadata;
 }else if(item.route==="/workspace/setup"){
   assert(!/\bweb\b|网页端/i.test(next.messages[locale]["page.workspaceSetup.description"]+" "+next.messages[locale]["setup.webNative"]));
 }else{
   const fixed=text(next.html)+" "+[...next.html.matchAll(/\b(?:title|aria-label)="([^"]*)"/g)].map(row=>row[1]).join(" ");
   assert.equal(fixed.match(technical)?.[0]??null,null,"Language settings must not explain implementation or testing");
   for(const name of ["portal-interface-locale-intro","portal-interface-locale-boundary","portal-interface-locale-support","portal-interface-locale-unsupported-code"])
     assert(!next.html.includes(name),"Remove only non-actionable duplicate sections: "+name);
   assert.equal((next.html.match(/type="radio"/g)||[]).length,3);
   for(const code of ["vi","en","zh"])assert(next.html.includes('name="locale" value="'+code+'"'));
   assert(next.html.includes("<fieldset")&&next.html.includes("<legend")&&next.html.includes('id="portal-interface-locale-save-help"'));
   for(const language of ["Tiếng Việt","English","中文"])assert(next.html.includes(language),"Preserve native language names");
   assert(!next.html.includes("<em>"),"Do not repeat the catalogue-review caption on each choice");
 }
});
test("only the declared existing dictionary values and one new three-language key can change",()=>{
 const before=old("vi","/account",{}).messages,after=current("vi","/account",{}).messages;
 const allowed=new Set(["page.account.description","page.workspaceSetup.description","setup.webNative","accountCenter.profile.upgradeEmailHelp",
  "accountCenter.profile.unlinkedBody","accountCenter.profile.profileFact","accountCenter.profile.dataControlsLink","accountCenter.profile.sessionFact",
  "accountCenter.profile.sessionLabel","accountCenter.profile.canonicalFact","page.interfaceLocale.description","interfaceLocale.formLegend",
  "interfaceLocale.formHelp","interfaceLocale.saveHelp","interfaceLocale.save"]);
 for(const locale of ["vi","en","zh"]){
   assert.deepEqual(Object.keys(after[locale]).filter(key=>!Object.hasOwn(before[locale],key)),["interfaceLocale.saveBlocked"]);
   for(const[key,value]of Object.entries(before[locale]))if(!allowed.has(key))assert.equal(after[locale][key],value,key);
   assert.equal(typeof after[locale]["interfaceLocale.saveBlocked"],"string");
 }
});
