import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {documentOcrCustomerHistoricalSource as inverse,documentOcrCustomerHistoricalSnapshot as snapshot} from "./helpers/document-ocr-customer-copy-snapshot.mjs";
import {documentConvertCustomerHistoricalSource as priorInverse,documentConvertCustomerHistoricalSnapshot as priorSnapshot} from "./helpers/document-convert-customer-copy-snapshot.mjs";
Error.stackTraceLimit=0;
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),".."),BASE="8ba0d0452f86dcc3d72e5087351134902eb4e659";
const fail=/Unreviewed Document OCR customer copy/,raw=fs.readFileSync(new URL("./fixtures/document-ocr-customer-copy-reviewed.json",import.meta.url));
const fixture=JSON.parse(raw),edits=fixture.canonicalChanges,rows=fixture.rows,keys=rows.map(row=>row[0]);
const lf=x=>x.replace(/\r\n/g,"\n"),hash=x=>createHash("sha256").update(x).digest("hex"),count=(s,p)=>s.split(p).length-1;
const files=["static/portal/portal.js","static/portal/portal-i18n.js","copyfast_pages.py"];
const before=Object.fromEntries(files.map(file=>[file,lf(execFileSync("git",["show",BASE+":"+file],{cwd:ROOT,encoding:"utf8",maxBuffer:30e6}))]));
const physical=Object.fromEntries(files.map(file=>[file,lf(fs.readFileSync(path.join(ROOT,file),"utf8"))]));
const candidate=Object.fromEntries(files.map(file=>{let source=before[file];for(const edit of edits.filter(value=>value.file===file)){assert.equal(count(source,edit.old),1);source=source.replace(edit.old,()=>edit.new);}return[file,source];}));
const functions=edits.filter(edit=>edit.file===files[0]&&edit.old.startsWith("  function ")),metadata=edits.filter(edit=>edit.file===files[0]&&!edit.old.startsWith("  function "));
const shell=edits.filter(edit=>edit.file===files[2]),catalogue=edits.find(edit=>edit.file===files[1]);
test("immutable four-worker R1 authority binds19exact edits/36rows with no worker failure or engine/output assertion",()=>{
 assert.equal(hash(raw),"2784e5ec2bf31f4921f4d39fd495175dbb9871f860947d1c9b363218a453839f");assert.equal(fixture.task,"DOCUMENT-OCR-CUSTOMER-COPY-20261119");assert.equal(fixture.base,BASE);assert.equal(fixture.revision,"ROOT_REVIEWED_R1");
 assert.equal(edits.length,19);assert.ok(edits.every(edit=>edit.count===1));assert.equal(rows.length,36);assert.equal(new Set(keys).size,36);
 assert.deepEqual(edits.reduce((out,edit)=>(out[edit.file]=(out[edit.file]||0)+1,out),{}),{[files[0]]:12,[files[2]]:6,[files[1]]:1});
 assert.deepEqual(fixture.sourceAuthorities.map(value=>[value.name,value.specId,value.revision,value.conversation,value.packetSha256,value.resultRawSha256]),[
  ["fields","DOCUMENT-OCR-SHARED-FIELDS-20261119","R1","e848b31b-be36-4038-8801-e3bd569b6b29","c35cda742efb7287c1737bee582eac8a1ad0e46cfa7bd02c0e47d4164e0c5c4d","87f4e7041cc8a92ffec0bcd13e193d03b4ccd694dcd8aac8d64e289d88ebdbc8"],
  ["image","DOCUMENT-OCR-IMAGE-PAGE-20261119","R1","3b569dc8-863e-47ca-a578-c0665a76b3c9","8f9c94a7b448617bdab9643637043fb8b8090b4b2b42b12d3dda627f0eb3fe3d","220fe68db72cf3727f73e98d0bc9bd871e6486ed748a0e6b0e90cfd0b062ee43"],
  ["pdf","DOCUMENT-OCR-PDF-PAGE-20261119","R1","569bac41-0255-4a3a-af0f-a46b54d013ae","d4e4e7a1f43cc9daf1c07f964fb5ae915ae788e4587cfd5f3546a4855fb7439d","a93d146a7b3bc65afcaeec608ac5190b0034c15a1b70821d4178f8a933ad37e3"],
  ["word","DOCUMENT-OCR-WORD-PAGE-20261119","R1","c37404c0-ba40-47b9-8a8e-acede81796f5","9a9024a141468f34578932c7525125bf0d62f49a7c29ce2e0eab0e6765bde8c4","eef2c0188026b68b944d080e70fd30468d7f272827c654fcff01025cf1205ebe"]]);
 assert.ok(fixture.sourceAuthorities.every(value=>value.schemaValid&&value.proposalExact&&value.applicationFailureCount===0&&value.applicationWrites===0&&value.verify==="NOT_RUN"));
 assert.equal(fixture.applicationWrites,0);assert.equal(fixture.engineRuntimeReadiness,"NOT_TESTED");assert.equal(fixture.finalOcrOutput,"NOT_TESTED");
});
for(const file of files)test(file+": actual current source equals BASE+19exact and inverse OLD/NEW/idempotence preserves outside bytes",()=>{
 assert.equal(physical[file],candidate[file],"Current source acceptance is independent of historical inversion");
 const pin=fixture.applicationBaseline.find(value=>value.file===file);assert.equal(hash(before[file]),pin.baselineLfSha256);assert.equal(hash(physical[file]),pin.candidateLfSha256);
 assert.equal(inverse(physical[file],file),before[file]);assert.equal(inverse(before[file],file),before[file]);assert.equal(inverse(inverse(physical[file],file),file),before[file]);
 const prefix="\r\n/* CUSTOMER media studio provider CSRF Facebook TikTok <b>&</b> */\r\n",suffix='\r\n/* CUSTOMER OCR scan private Asset Vault literal */\r\n';
 for(const source of [physical[file],before[file]])assert.equal(inverse(prefix+source+suffix,file),prefix+before[file]+suffix);
 assert.equal(inverse(prefix+suffix,file),prefix+suffix);assert.ok(inverse(physical[file]+suffix,file).endsWith(suffix));assert.notEqual(inverse(physical[file]+suffix,file),before[file]);assert.equal(inverse(physical[file],"customer/unrelated.txt"),physical[file]);
});
test("151actual source pins preserve148protected files without any inverse or acceptance mask",()=>{
 assert.equal(fixture.applicationBaseline.length,151);assert.equal(fixture.applicationBaseline.filter(pin=>pin.changed).length,3);
 for(const pin of fixture.applicationBaseline){assert.equal(hash(lf(fs.readFileSync(path.join(ROOT,pin.file),"utf8"))),pin.candidateLfSha256,pin.file);assert.equal(pin.changed,pin.baselineLfSha256!==pin.candidateLfSha256);if(!files.includes(pin.file))assert.equal(pin.baselineLfSha256,pin.candidateLfSha256);}
});
test("six complete field/render functions reject missing mixed changed duplicate detached reordered and next-owner faults",()=>{
 const file=files[0],current=candidate[file],nextOwners={imageOcrFormFields:"pdfToImagesFormFields",pdfOcrFormFields:"pdfOcrWordFormFields",pdfOcrWordFormFields:"storyboardGridFormValues",renderImageOcr:"renderPdfOcr",renderPdfOcr:"renderPdfOcrToWord",renderPdfOcrToWord:"renderImageToPdf"};
 for(const edit of functions){
  const name=edit.old.match(/^  function (\w+)\(/)[1],next="  function "+nextOwners[name]+"(";
  for(const malformed of [current.replace(edit.new,""),current.replace(edit.new,()=>edit.old),current.replace(edit.new,edit.new.replace("docOcr","docOcrUNKNOWN")),current+"\n"+edit.new,current.replace(edit.new,"")+"\n"+edit.new,current.replace(next,"  function UNKNOWN_NEXT("),current.replace(edit.new,edit.new.replace("  function "+name+"(","  function UNKNOWN_OWNER("))])assert.throws(()=>inverse(malformed,file),fail);
 }
 const[a,b]=functions,marker="@@OCR_FUNCTION_SWAP@@";assert.throws(()=>inverse(current.replace(a.new,marker).replace(b.new,()=>a.new).replace(marker,()=>b.new),file),fail);
 assert.equal(inverse("/* older unowned portal */",file),"/* older unowned portal */");
});
test("six JS metadata insertions reject changed partial duplicate detached reordered and owner mutations",()=>{
 const file=files[0],current=candidate[file];
 for(const edit of metadata){const extra=edit.new.slice(0,-edit.old.length);for(const malformed of [current.replace(edit.new,()=>edit.old),current.replace(edit.new,edit.new.replace("docOcr","docOcrUNKNOWN")),current+"\n"+edit.new,current.replace(edit.new,"")+"\n"+edit.new,current.replace(edit.new,extra+"\n/* detached */\n"+edit.old)])assert.throws(()=>inverse(malformed,file),fail);}
 const[a,b]=metadata.filter(edit=>edit.old.includes("Title")),marker="@@OCR_METADATA_SWAP@@";assert.throws(()=>inverse(current.replace(a.new,marker).replace(b.new,()=>a.new).replace(marker,()=>b.new),file),fail);
 for(const owner of ["localizedPageTitle","localizedPageDescription"])assert.throws(()=>inverse(current.replace("  function "+owner+"(","  function UNKNOWN_META_OWNER("),file),fail);
});
test("six server shell entries reject partial changed duplicate detached reordered and wrong-owner placements",()=>{
 const file=files[2],current=candidate[file];
 for(const edit of shell)for(const malformed of [current.replace(edit.new,()=>edit.old),current.replace(edit.new,edit.new.replace("/documents/","/documents/UNKNOWN-")),current+"\n"+edit.new,current.replace(edit.new,"")+"\n"+edit.new,current.replace(edit.new,edit.new.slice(0,-edit.old.length)+"\n# detached\n"+edit.old)])assert.throws(()=>inverse(malformed,file),fail);
 const[a,b]=shell.filter(edit=>!edit.old.includes("\n")),marker="@@OCR_SHELL_SWAP@@";assert.throws(()=>inverse(current.replace(a.new,marker).replace(b.new,()=>a.new).replace(marker,()=>b.new),file),fail);
 for(const owner of ["_PORTAL_SHELL_TITLES = {","_PORTAL_SHELL_DESCRIPTIONS = {"])assert.throws(()=>inverse(current.replace(owner,"UNKNOWN_SHELL = {"),file),fail);
});
test("108exact catalog declarations reject partial unknown changed duplicate detached reordered or post-freeze variants",()=>{
 const file=files[1],current=candidate[file],chunk=catalogue.new.slice(0,-catalogue.old.length),first=rows[0][0],second=rows[1][0],marker="@@OCR_KEY_SWAP@@";
 for(const malformed of [current.replace(chunk,chunk.replace('"'+first+'":','"docOcrUNKNOWN":')),current.replace(chunk,chunk.replace(rows[0][1],"UNKNOWN_VALUE")),current+"\n"+catalogue.new,current.replace(chunk,"")+"\n"+chunk,current.replace(chunk,chunk.split("\n").reverse().join("\n")),current.replace(catalogue.new,catalogue.new+"\n/* detached */")])assert.throws(()=>inverse(malformed,file),fail);
 assert.throws(()=>inverse(current.replace('"'+first+'":',marker).replace('"'+second+'":','"'+first+'":').replace(marker,'"'+second+'":'),file),fail);
 assert.throws(()=>inverse(current.replace(chunk,chunk.replace(new RegExp('"'+first+'":"[^"]*",'),"")),file),fail);
 assert.equal(inverse(current.replace(chunk,""),file),before[file],"Whole absent addition is OLD");
});
for(const[locale,index]of [["vi",1],["en",2],["zh",3]]){
 test(locale+": snapshot removes exactly36owned entries and preserves unknown customer entries and identities",()=>{
  const first=Object.freeze(["CUSTOMER Facebook TikTok","media studio provider OCR"]),last=Object.freeze(["customer.docOcrUnknown","literal <b>&</b>"]),owned=rows.map(row=>Object.freeze([row[0],row[index]])),entries=Object.freeze([first,...owned,last]),prior=[first,last];
  assert.deepEqual(snapshot(entries,locale),prior);assert.strictEqual(snapshot(entries,locale)[0],first);assert.strictEqual(snapshot(entries,locale).at(-1),last);assert.strictEqual(snapshot(prior,locale),prior);assert.deepEqual(priorSnapshot(entries,locale),prior);
 });
 test(locale+": snapshot rejects partial changed duplicate reordered and unknown owned prefix keys",()=>{
  const owned=rows.map(row=>[row[0],row[index]]);
  for(const malformed of [owned.slice(1),owned.slice(0,-1),[...owned,owned[0]],owned.map((entry,at)=>at===0?[entry[0],"UNKNOWN"]:entry),[owned[1],owned[0],...owned.slice(2)],owned.map((entry,at)=>at===0?[entry[0]+"UNKNOWN",entry[1]]:entry),[...owned,["docOcrUNKNOWN","literal"]]])assert.throws(()=>snapshot(malformed,locale),fail);
 });
}
test("new type/locale guards and prior DCC guard identities stay separate",()=>{
 assert.throws(()=>inverse(null,files[0]),fail);assert.throws(()=>snapshot([],"fr"),fail);assert.throws(()=>snapshot(null,"vi"),fail);
 assert.throws(()=>priorInverse(null,files[0]),/Unreviewed Document Convert customer copy/);assert.throws(()=>priorSnapshot([],"fr"),/Unreviewed Document Convert customer copy/);assert.throws(()=>priorSnapshot(null,"vi"),/Unreviewed Document Convert customer copy/);
});
test("marker-free OLD DCC malformed metadata/next-owner source passes OCR leaf and keeps the prior DCC error",()=>{
 const file=files[0],legacy=before[file],prior=JSON.parse(fs.readFileSync(new URL("./fixtures/document-convert-customer-copy-reviewed.json",import.meta.url)));
 const edit=prior.canonicalChanges.find(value=>value.file===file&&value.old.startsWith('    if (path === "/documents/split")')&&value.old.includes("Title"));assert.ok(edit);
 for(const malformed of [legacy.replace(edit.new,()=>edit.old),legacy.replace("  function imageOcrFormFields(","  function UNKNOWN_PRIOR_NEXT(")]){
  assert.notEqual(malformed,legacy);assert.doesNotMatch(malformed,/\buiText\(["']docOcr/);assert.equal(inverse(malformed,file),malformed);assert.throws(()=>priorInverse(malformed,file),/Unreviewed Document Convert customer copy/);
 }
});
test("actual complete dictionaries initialize36values before freeze and preserve equal VI/EN/ZH keysets",()=>{
 const document={title:"",documentElement:{lang:"vi",setAttribute(){}}},window={document,navigator:{language:"vi"},dispatchEvent(){},CustomEvent:function(){}};
 vm.runInContext(physical[files[1]],vm.createContext({window,document,Intl,Date,Number,String,Object,Array,Set,Map,Math,RegExp}));
 const messages=window.TOANAASI18n.messages;
 for(const[locale,index]of [["vi",1],["en",2],["zh",3]]){assert.equal(Object.isFrozen(messages[locale]),true);for(const row of rows)assert.equal(messages[locale][row[0]],row[index]);}
 assert.deepEqual(Object.keys(messages.vi).sort(),Object.keys(messages.en).sort());assert.deepEqual(Object.keys(messages.vi).sort(),Object.keys(messages.zh).sort());
});
