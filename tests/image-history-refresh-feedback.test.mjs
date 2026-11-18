import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import test from "node:test";
import {createHash} from "node:crypto";
import {fileURLToPath} from "node:url";
// This proves the ACTUAL complete toast function only: NOT full action/dispatch/native behavior.
const ROOT=fileURLToPath(new URL("..",import.meta.url)).replace(/[\\/]$/,"");
const AUTHORITY=new URL("./fixtures/image-history-refresh-feedback-reviewed.json",import.meta.url);
const SHA="d23dc6e3acd6365400205e60debad8564325d73b78af44c1253ecf8564c24d9a",SPEC="IMAGE-HISTORY-REFRESH-FEEDBACK-20261119";
const authorityRaw=fs.readFileSync(AUTHORITY),authority=JSON.parse(authorityRaw),proposal=authority.proposal,edits=proposal.changes;
const sources={integration:fs.readFileSync(path.join(ROOT,"static/portal/integration.js"),"utf8").replace(/\r\n/g,"\n"),i18n:fs.readFileSync(path.join(ROOT,"static/portal/portal-i18n.js"),"utf8").replace(/\r\n/g,"\n")},prior={...sources};
const count=(text,part)=>text.split(part).length-1,files={"static/portal/integration.js":"integration","static/portal/portal-i18n.js":"i18n"};
const additions=edits.map(edit=>{assert.equal(edit.count,1);assert.ok(Object.hasOwn(files,edit.file));const prefix=edit.new.startsWith(edit.old),suffix=edit.new.endsWith(edit.old);assert.ok(prefix!==suffix);const chunk=prefix?edit.new.slice(edit.old.length):edit.new.slice(0,-edit.old.length);assert.ok(chunk);assert.equal(count(sources[files[edit.file]],edit.old),1);return{key:files[edit.file],chunk,anchor:edit.old};});
const present=additions.map(({key,chunk})=>count(sources[key],chunk));assert.ok(present.every(n=>n===0)||present.every(n=>n===1),"All-OLD or all-NEW finite additions only");
if(present.every(n=>n===1))for(const{key,chunk,anchor}of [...additions].reverse()){assert.equal(count(prior[key],chunk),1);const index=prior[key].indexOf(chunk);prior[key]=prior[key].slice(0,index)+prior[key].slice(index+chunk.length);assert.equal(count(prior[key],anchor),1);}
const CASES=[
  ["imageHistoryRefreshed","Đã làm mới lịch sử ảnh Web.","Đã làm mới lịch sử ảnh.","Image history refreshed.","图像记录已刷新。"],
  ["imageHistoryRefreshFailed","Không thể làm mới lịch sử ảnh Web.","Chưa làm mới được lịch sử ảnh. Hãy thử lại.","Couldn't refresh image history. Try again.","未能刷新图像记录。请重试。"],
  ["imageHistoryAccessDenied","Bạn không có quyền xem lịch sử ảnh Web.","Hãy kiểm tra quyền truy cập để xem lịch sử ảnh.","Check your access to view image history.","请检查您的访问权限以查看图像记录。"]
];
function toastCode(source){const start=source.indexOf("  function toast(message, type) {"),end=source.indexOf("\n  }",start)+4;assert.ok(start>=0&&end>start);const code=source.slice(start,end);assert.equal(count(code,"function toast(message, type)"),1);assert.ok(code.endsWith("window.setTimeout(() => node.remove(), 6500);\n  }"));return code;}
const actualCode=toastCode(sources.integration),priorCode=toastCode(prior.integration);
function deepFreeze(value){if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.freeze(value);for(const child of Object.values(value))deepFreeze(child);}return value;}
function runtime(locale,physical=sources,translationMode=null){
  const nodes=[],timers=[],noop=()=>{},region={querySelectorAll:()=>[...nodes],appendChild:node=>nodes.push(node)};
  const document={readyState:"loading",addEventListener:noop,documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null},body:{classList:{add:noop,remove:noop}},querySelector:selector=>selector==="[data-portal-toast]"?region:null,
    createElement:tag=>{assert.equal(tag,"div");return{className:"",textContent:"",attributes:{},set innerHTML(_){throw Error("HTML insertion is forbidden");},setAttribute(key,value){this.attributes[key]=value;},remove(){const index=nodes.indexOf(this);if(index>=0)nodes.splice(index,1);}};}};
  const window={document,navigator:{language:locale},location:{pathname:"/image/history",search:""},localStorage:{getItem:()=>null,setItem:noop},addEventListener:noop,dispatchEvent:noop,setTimeout:(fn,ms)=>{timers.push({fn,ms});return timers.length;}};
  const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Intl,console,fetch:()=>{throw Error("Network forbidden");}});
  vm.runInContext(physical.i18n,sandbox);window.TOANAASI18n.setLocale(locale,{emit:false});deepFreeze(window.TOANAASI18n.messages);
  // The physical i18n global is non-writable. A function-local window stand-in
  // models a missing/empty translator without changing that locked global.
  sandbox.__toastWindow=translationMode?Object.create(window,{TOANAASI18n:{value:Object.freeze({t:()=>translationMode==="missing"?undefined:""})}}):window;
  const toast=vm.runInContext("(function(window){return ("+toastCode(physical.integration)+");})(__toastWindow)",sandbox);
  return{toast,nodes,timers,window,setLocale:value=>window.TOANAASI18n.setLocale(value,{emit:false}),clear(){for(const timer of timers)timer.fn();timers.length=0;assert.equal(nodes.length,0);}};
}
const view=r=>r.nodes.map(node=>({text:node.textContent,className:node.className,role:node.attributes.role}));
for(const[locale,index]of [["vi",2],["en",3],["zh",4]]){
  for(const row of CASES)test(`${locale}/${row[0]}: actual toast function fixed copy, status/error semantics, textContent and timer`,()=>{
    for(const type of [undefined,"error"]){const r=runtime(locale),input=Object.freeze({toString:()=>row[1]});r.toast(input,type);assert.equal(r.nodes.length,1);assert.deepEqual(view(r),[{text:row[index],className:"portal-toast"+(type==="error"?" portal-toast--warning":""),role:type==="error"?"alert":"status"}]);assert.equal(r.timers.length,1);assert.equal(r.timers[0].ms,6500);r.timers[0].fn();assert.equal(r.nodes.length,0);}
  });
  for(const mode of ["missing","empty"])test(`${locale}/${mode}: missing translation uses exact VI fallback for all three messages`,()=>{
    for(const row of CASES){const r=runtime(locale,sources,mode);r.toast(row[1],"error");assert.equal(r.nodes[0].textContent,row[2]);assert.equal(r.nodes[0].attributes.role,"alert");assert.equal(r.timers[0].ms,6500);}
  });
  test(`${locale}: duplicate/class-specific dedup, maximum two visible and self-removal stay physical`,()=>{
    const r=runtime(locale);r.toast(CASES[0][1]);r.toast(CASES[0][1]);assert.equal(r.nodes.length,1);assert.equal(r.timers.length,1);r.toast(CASES[0][1],"error");assert.equal(r.nodes.length,2);assert.equal(r.timers.length,2);r.clear();
    for(const row of CASES)r.toast(row[1],"error");assert.equal(r.nodes.length,2);assert.deepEqual(r.nodes.map(node=>node.textContent),CASES.slice(1).map(row=>row[index]));assert.equal(r.timers.length,3);assert.ok(r.timers.every(timer=>timer.ms===6500));r.clear();
  });
  test(`${locale}: unknown customer/markup/prototype and near-match remain literal text`,()=>{
    const values=['CUSTOMER Facebook TikTok <b>keep & text</b>',"__proto__","constructor","toString",...CASES.flatMap(row=>[row[1]+"!",row[1].slice(0,-1)])];
    for(const text of values){const r=runtime(locale);r.toast(text);assert.deepEqual(view(r),[{text,className:"portal-toast",role:"status"}]);assert.equal(r.timers[0].ms,6500);r.clear();}
  });
  test(`${locale}: every unrelated physical prior fixed bridge message preserves its output/role/class/timer`,()=>{
    const start=priorCode.indexOf("    const legacyStatusMap = {"),end=priorCode.indexOf("\n    };",start);assert.ok(start>=0&&end>start);const object=priorCode.slice(start+"    const legacyStatusMap = ".length,end+6);const map=vm.runInNewContext("("+object.replace(/;$/,"")+")"),old=runtime(locale,prior),now=runtime(locale);
    assert.ok(Object.keys(map).length>=13);for(const message of Object.keys(map)){assert.ok(!CASES.some(row=>row[1]===message));for(const type of [undefined,"error"]){old.toast(message,type);now.toast(message,type);assert.deepEqual(view(now),view(old));assert.deepEqual(now.timers.map(timer=>timer.ms),old.timers.map(timer=>timer.ms));old.clear();now.clear();}}
  });
}
for(const row of CASES)test(`${row[0]}: same VM takes locale at call time, not extraction time`,()=>{
  const r=runtime("vi");for(const[locale,index]of [["en",3],["zh",4],["vi",2]]){r.setLocale(locale);r.toast(row[1]);assert.equal(r.nodes[0].textContent,row[index]);r.clear();}
});
test("feedback authority and complete physical toast extraction stay within exact three additions",()=>{
  assert.equal(createHash("sha256").update(authorityRaw).digest("hex"),SHA);assert.equal(authority.review.schemaValid,true);assert.equal(authority.review.proposalExact,true);assert.equal(authority.review.specId,SPEC);assert.equal(authority.review.conversation,"11cba0b5-2678-4a9c-ae4e-cae51aa2479f");assert.equal(proposal.specId,SPEC);assert.equal(proposal.revision,"R1");assert.equal(edits.length,3);assert.deepEqual(edits.map(row=>row.file),["static/portal/integration.js","static/portal/integration.js","static/portal/portal-i18n.js"]);
  for(const row of CASES){assert.ok(edits[0].new.includes(JSON.stringify(row[1])+": "+JSON.stringify(row[0])));for(const value of row.slice(2))assert.ok(edits[2].new.includes(JSON.stringify(value)));}
  assert.ok(actualCode.startsWith("  function toast(message, type) {"));assert.equal(count(actualCode,"node.textContent = displayText;"),1);assert.equal(count(actualCode,"window.setTimeout(() => node.remove(), 6500);"),1);
});
