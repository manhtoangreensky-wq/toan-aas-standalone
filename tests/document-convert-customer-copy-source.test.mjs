import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {documentOcrCustomerHistoricalSource} from "./helpers/document-ocr-customer-copy-snapshot.mjs";
import {documentConvertCustomerHistoricalSource as inverse,documentConvertCustomerHistoricalSnapshot as snapshot} from "./helpers/document-convert-customer-copy-snapshot.mjs";
import {imageEditCustomerHistoricalSource as editInverse,imageEditCustomerHistoricalSnapshot as editSnapshot} from "./helpers/image-edit-customer-copy-snapshot.mjs";
import {pdfUtilitiesCustomerHistoricalSource as pdfInverse,pdfUtilitiesCustomerHistoricalSnapshot as pdfSnapshot} from "./helpers/pdf-utilities-customer-copy-snapshot.mjs";
Error.stackTraceLimit=0;
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),".."),BASE="a589008be5d7be371789551ffc11e750db46270b";
const fail=/Unreviewed Document Convert customer copy/,raw=fs.readFileSync(new URL("./fixtures/document-convert-customer-copy-reviewed.json",import.meta.url));
const fixture=JSON.parse(raw),edits=fixture.canonicalChanges,rows=fixture.rows,keys=rows.map(row=>row[0]);
const lf=x=>x.replace(/\r\n/g,"\n"),hash=x=>createHash("sha256").update(x).digest("hex"),count=(s,p)=>s.split(p).length-1;
const files=["static/portal/portal.js","static/portal/portal-i18n.js","copyfast_pages.py"];
const before=Object.fromEntries(files.map(file=>[file,lf(execFileSync("git",["show",BASE+":"+file],{cwd:ROOT,encoding:"utf8",maxBuffer:30e6}))]));
const currentPhysical=Object.fromEntries(files.map(file=>[file,lf(fs.readFileSync(path.join(ROOT,file),"utf8"))]));
// Historical DCC source comparator only; current OCR acceptance uses separate full physical sources.
const physical=Object.fromEntries(files.map(file=>[file,documentOcrCustomerHistoricalSource(currentPhysical[file],file)]));
const candidate=Object.fromEntries(files.map(file=>{let source=before[file];for(const edit of edits.filter(value=>value.file===file)){assert.equal(count(source,edit.old),1);source=source.replace(edit.old,()=>edit.new);}return[file,source];}));
const functions=edits.filter(edit=>edit.file===files[0]&&edit.old.startsWith("  function "));
const metadata=edits.filter(edit=>edit.file===files[0]&&!edit.old.startsWith("  function ")),shell=edits.filter(edit=>edit.file===files[2]),catalogue=edits.find(edit=>edit.file===files[1]);
test("immutable three-worker R1 authority binds13exact edits,28rows and zero application failures",()=>{
 assert.equal(hash(raw),"e162e15e4ddff0899dcf69bee7134576c7fac7a2fb35fb1857e555d1e70c6b63");assert.equal(fixture.task,"DOCUMENT-CONVERT-CUSTOMER-COPY-20261119");assert.equal(fixture.base,BASE);assert.equal(fixture.revision,"ROOT_REVIEWED_R1");
 assert.equal(edits.length,13);assert.ok(edits.every(edit=>edit.count===1));assert.equal(rows.length,28);assert.equal(new Set(keys).size,28);
 assert.deepEqual(edits.reduce((out,edit)=>(out[edit.file]=(out[edit.file]||0)+1,out),{}),{[files[0]]:8,[files[2]]:4,[files[1]]:1});
 assert.deepEqual(fixture.sourceAuthorities.map(value=>[value.name,value.specId,value.revision,value.conversation,value.packetSha256,value.resultRawSha256]),[
  ["fields","DOCUMENT-CONVERT-FIELDS-20261119","R1","4016959a-13b1-4e7f-8289-56378a80fb0c","63ef1c873eef4f7468069b9dc9a6a68457f3c78e119d370d0c4c55f5e967cac7","e45d1562702d5a273aebdf119f47477bdcf4b42d18e542a4007eb5b3ed2c1138"],
  ["images","DOCUMENT-CONVERT-IMAGES-PAGE-20261119","R1","523ff7c6-8df9-4a1b-8aae-3ac0078bb922","6575c16760853c03d5ca3d82d5b021b40f101cd5552826ae5182865ba4fe7d77","40fe39546c9973a700cb5a6e230c53a0604be373c9b2f3b7e6a9bc8bfb0d7b6a"],
  ["word","DOCUMENT-CONVERT-WORD-PAGE-20261119","R1","f5e057f5-c42e-4072-8794-27a4fd1da479","07d7d1c50f0a1a701b8febd863518c54c8d9c98044886331b2a7f3958b60bbd9","9dda1cdfb7c6117a12efacd4e5c8f87b34a5b24c11ac6bb246ea137efea19ca8"]]);
 assert.ok(fixture.sourceAuthorities.every(value=>value.schemaValid&&value.proposalExact&&value.applicationFailureCount===0&&value.applicationWrites===0&&value.verify==="NOT_RUN"));assert.equal(fixture.applicationWrites,0);
});
for(const file of files)test(file+": full physical source equals GitBASE+finite13; inverse OLD/NEW/idempotence preserves every outside byte",()=>{
 assert.equal(physical[file],candidate[file],"Current source is physical; no source acceptance projection");
 const pin=fixture.applicationBaseline.find(value=>value.file===file);assert.equal(hash(before[file]),pin.baselineLfSha256);assert.equal(hash(physical[file]),pin.candidateLfSha256);
 assert.equal(inverse(physical[file],file),before[file]);assert.equal(inverse(before[file],file),before[file]);assert.equal(inverse(inverse(physical[file],file),file),before[file]);
 const prefix="\r\n/* CUSTOMER Facebook TikTok media studio provider CSRF <b>&</b> */\r\n",suffix='\r\n/* CUSTOMER Asset Vault Signed session storage parser */\r\n';
 for(const source of [physical[file],before[file]])assert.equal(inverse(prefix+source+suffix,file),prefix+before[file]+suffix);
 assert.equal(inverse(prefix+suffix,file),prefix+suffix);assert.ok(inverse(physical[file]+suffix,file).endsWith(suffix));assert.notEqual(inverse(physical[file]+suffix,file),before[file]);assert.equal(inverse(physical[file],"customer/unrelated.txt"),physical[file]);
});
test("151source pins protect148unchanged application files and exactly3changed sources",()=>{
 assert.equal(fixture.applicationBaseline.length,151);assert.equal(fixture.applicationBaseline.filter(pin=>pin.changed).length,3);
 for(const pin of fixture.applicationBaseline){
  const actual=lf(fs.readFileSync(path.join(ROOT,pin.file),"utf8"));
  assert.equal(hash(files.includes(pin.file)?documentOcrCustomerHistoricalSource(actual,pin.file):actual),pin.candidateLfSha256,pin.file);
  assert.equal(pin.changed,pin.baselineLfSha256!==pin.candidateLfSha256);
  if(!files.includes(pin.file))assert.equal(pin.baselineLfSha256,pin.candidateLfSha256);
 }
});
test("four complete functions reject missing changed mixed duplicate detached reordered and next-owner faults",()=>{
 const file=files[0],current=candidate[file],nextOwners={pdfToWordFormFields:"imageOcrFormFields",pdfToImagesFormFields:"imageToPdfFormFields",renderPdfToImages:"renderPdfToWord",renderPdfToWord:"renderImageOcr"};
 for(const edit of functions){
  const name=edit.old.match(/^  function (\w+)\(/)[1],next="  function "+nextOwners[name]+"(";
  for(const malformed of [current.replace(edit.new,""),current.replace(edit.new,()=>edit.old),current.replace(edit.new,edit.new.replace("docConvert","docConvertUNKNOWN")),current+"\n"+edit.new,current.replace(edit.new,"")+"\n"+edit.new,current.replace(next,"  function UNKNOWN_NEXT("),current.replace(edit.new,edit.new.replace("  function "+name+"(","  function UNKNOWN_OWNER("))])assert.throws(()=>inverse(malformed,file),fail);
 }
 const[a,b]=functions,marker="@@DOC_CONVERT_FUNCTION_SWAP@@";assert.throws(()=>inverse(current.replace(a.new,marker).replace(b.new,()=>a.new).replace(marker,()=>b.new),file),fail);
 assert.equal(inverse("/* older unowned portal boundary */",file),"/* older unowned portal boundary */");
});
test("four JS metadata insertions reject missing changed duplicate detached reordered and owner faults",()=>{
 const file=files[0],current=candidate[file];
 for(const edit of metadata){
  const extra=edit.new.slice(0,-edit.old.length);
  for(const malformed of [current.replace(edit.new,()=>edit.old),current.replace(edit.new,edit.new.replace("docConvert","docConvertUNKNOWN")),current+"\n"+edit.new,current.replace(edit.new,"")+"\n"+edit.new,current.replace(edit.new,extra+"\n/* detached */\n"+edit.old)])assert.throws(()=>inverse(malformed,file),fail);
 }
 const[a,b]=metadata.filter(edit=>edit.old.includes("Title")),marker="@@DOC_CONVERT_METADATA_SWAP@@";
 assert.throws(()=>inverse(current.replace(a.new,marker).replace(b.new,()=>a.new).replace(marker,()=>b.new),file),fail);
 for(const owner of ["localizedPageTitle","localizedPageDescription"])assert.throws(()=>inverse(current.replace("  function "+owner+"(","  function UNKNOWN_META_OWNER("),file),fail);
});
test("four server title/description dictionary entries reject partial changed duplicate detached reordered and owner faults",()=>{
 const file=files[2],current=candidate[file];
 for(const edit of shell){
  for(const malformed of [current.replace(edit.new,()=>edit.old),current.replace(edit.new,edit.new.replace("PDF","UNKNOWN_PDF")),current+"\n"+edit.new,current.replace(edit.new,"")+"\n"+edit.new,current.replace(edit.new,edit.new.slice(0,-edit.old.length)+"\n# detached\n"+edit.old)])assert.throws(()=>inverse(malformed,file),fail);
 }
 const[a,b]=shell.filter(edit=>!edit.old.includes("\n")),marker="@@DOC_CONVERT_SHELL_SWAP@@";
 assert.throws(()=>inverse(current.replace(a.new,marker).replace(b.new,()=>a.new).replace(marker,()=>b.new),file),fail);
 for(const owner of ["_PORTAL_SHELL_TITLES = {","_PORTAL_SHELL_DESCRIPTIONS = {"])assert.throws(()=>inverse(current.replace(owner,"UNKNOWN_SHELL = {"),file),fail);
 assert.equal(inverse("/* older unowned pages boundary */",file),"/* older unowned pages boundary */");
});
test("exact catalogue rejects partial changed unknown duplicate detached reordered and post-freeze mutations",()=>{
 const file=files[1],current=candidate[file],chunk=catalogue.new.slice(0,-catalogue.old.length),first=rows[0][0],second=rows[1][0],marker="@@DOC_CONVERT_KEY_SWAP@@";
 for(const malformed of [current.replace(chunk,chunk.replace('"'+first+'":','"docConvertUNKNOWN":')),current.replace(chunk,chunk.replace(rows[0][1],"UNKNOWN_VALUE")),current+"\n"+catalogue.new,current.replace(chunk,"")+"\n"+chunk,current.replace(chunk,chunk.split("\n").reverse().join("\n")),current.replace(catalogue.new,catalogue.new+"\n/* detached */")])assert.throws(()=>inverse(malformed,file),fail);
 assert.throws(()=>inverse(current.replace('"'+first+'":',marker).replace('"'+second+'":','"'+first+'":').replace(marker,'"'+second+'":'),file),fail);
 const shortened=chunk.replace(new RegExp('"'+first+'":"[^"]*",'),"");assert.throws(()=>inverse(current.replace(chunk,shortened),file),fail);
 assert.equal(inverse(current.replace(chunk,""),file),before[file],"Entire absent new catalog is legitimate OLD");
});
for(const[locale,index]of [["vi",1],["en",2],["zh",3]]){
 test(locale+": snapshot removes exactly28owned entries, preserves unknown unrelated customer entries and input identities",()=>{
  const first=Object.freeze(["CUSTOMER Facebook TikTok","media studio provider CSRF"]),last=Object.freeze(["customer.docConvertUnknown","Asset Vault literal <b>&</b>"]);
  const owned=rows.map(row=>Object.freeze([row[0],row[index]])),entries=Object.freeze([first,...owned,last]),prior=[first,last];
  assert.deepEqual(snapshot(entries,locale),prior);assert.strictEqual(snapshot(entries,locale)[0],first);assert.strictEqual(snapshot(entries,locale).at(-1),last);assert.strictEqual(snapshot(prior,locale),prior);
  assert.deepEqual(editSnapshot(entries,locale),prior);assert.deepEqual(pdfSnapshot(entries,locale),prior);
 });
 test(locale+": snapshot rejects partial changed duplicate reordered and unknown prefixed entries",()=>{
  const owned=rows.map(row=>[row[0],row[index]]);
  for(const malformed of [owned.slice(1),owned.slice(0,-1),[...owned,owned[0]],owned.map((entry,at)=>at===0?[entry[0],"UNKNOWN"]:entry),[owned[1],owned[0],...owned.slice(2)],owned.map((entry,at)=>at===0?[entry[0]+"UNKNOWN",entry[1]]:entry),[...owned,["docConvertUNKNOWN","literal"]]])assert.throws(()=>snapshot(malformed,locale),fail);
 });
}
test("original Edit and PDF type/locale guard errors precede the new finite leaf",()=>{
 assert.throws(()=>inverse(null,files[0]),fail);assert.throws(()=>snapshot([],"fr"),fail);assert.throws(()=>snapshot(null,"vi"),fail);
 assert.throws(()=>editInverse(null,files[0]),/Unreviewed Image Edit customer copy/);assert.throws(()=>editSnapshot([],"fr"),/Unreviewed Image Edit customer copy/);assert.throws(()=>editSnapshot(null,"vi"),/Unreviewed Image Edit customer copy/);
 assert.throws(()=>pdfInverse(null,files[0]),/Unreviewed PDF utilities customer copy/);assert.throws(()=>pdfSnapshot([],"fr"),/Unreviewed PDF utilities customer copy/);assert.throws(()=>pdfSnapshot(null,"vi"),/Unreviewed PDF utilities customer copy/);
});
test("marker-free OLD PDF owner mutations pass the newest leaf and retain the original PDF failure identity",()=>{
 const file=files[0],legacy=editInverse(before[file],file),pdfFixture=JSON.parse(fs.readFileSync(new URL("./fixtures/pdf-utilities-customer-copy-reviewed.json",import.meta.url)));
 const field=pdfFixture.canonicalChanges.find(edit=>edit.file===file&&edit.new.startsWith("  function imageToPdfFormFields("));assert.ok(field);assert.equal(count(legacy,field.new),1);
 for(const malformed of [legacy.replace(field.new,""),legacy.replace("  function renderPdfToImages(","  function UNKNOWN_PRIOR_NEXT(")]){
  assert.notEqual(malformed,legacy);assert.doesNotMatch(malformed,/\buiText\(["']docConvert/);
  assert.equal(inverse(malformed,file),malformed,"No owned new marker means the older contract remains responsible");
  assert.throws(()=>pdfInverse(malformed,file),/Unreviewed PDF utilities customer copy/);
 }
});
