import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {documentConvertCustomerHistoricalSource} from "./helpers/document-convert-customer-copy-snapshot.mjs";
import {imageEditCustomerHistoricalSource as inverse,imageEditCustomerHistoricalSnapshot as snapshot} from "./helpers/image-edit-customer-copy-snapshot.mjs";
import {pdfUtilitiesCustomerHistoricalSource as pdfInverse,pdfUtilitiesCustomerHistoricalSnapshot as pdfSnapshot} from "./helpers/pdf-utilities-customer-copy-snapshot.mjs";
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),".."),BASE="f8932643c1408d6565a0f1574f9bdd47ffac267b",fail=/Unreviewed Image Edit customer copy/;
const raw=fs.readFileSync(new URL("./fixtures/image-edit-customer-copy-reviewed.json",import.meta.url)),fixture=JSON.parse(raw),edits=fixture.canonicalChanges;
const lf=value=>value.replace(/\r\n/g,"\n"),hash=value=>createHash("sha256").update(value).digest("hex"),count=(source,part)=>source.split(part).length-1;
const files=["static/portal/portal.js","static/portal/portal-i18n.js","static/portal/portal.css"];
const before=Object.fromEntries(files.map(file=>[file,lf(execFileSync("git",["show",BASE+":"+file],{cwd:ROOT,encoding:"utf8",maxBuffer:30e6}))])),currentPhysical=Object.fromEntries(files.map(file=>[file,lf(fs.readFileSync(path.join(ROOT,file),"utf8"))]));
// Historical source comparator only; this suite has no current renderer inputs.
const physical=Object.fromEntries(files.map(file=>[file,documentConvertCustomerHistoricalSource(currentPhysical[file],file)]));
const ordered=[...fixture.pageRows,...fixture.fieldsRows],keys=ordered.map(row=>row[0]),rows=edits.filter(edit=>edit.file===files[1]).map(edit=>({...edit,oldRow:JSON.parse(edit.old.trim().replace(/,$/,"")),newRow:JSON.parse(edit.new.trim().replace(/,$/,""))})).sort((a,b)=>keys.indexOf(a.oldRow[0])-keys.indexOf(b.oldRow[0]));
test("immutable three-worker authority binds22changes/20rows and keeps the single recorded R1 correction",()=>{
  assert.equal(hash(raw),"7032192534419999f7528e3a6dbf08151b5db6ed96b3c49c7ecb300a6434007f");assert.equal(fixture.base,BASE);assert.equal(fixture.task,"IMAGE-EDIT-CUSTOMER-CLEANUP-20261119");
  assert.equal(edits.length,22);assert.ok(edits.every(edit=>edit.count===1));assert.deepEqual(edits.reduce((out,edit)=>(out[edit.file]=(out[edit.file]||0)+1,out),{}),{[files[1]]:20,[files[0]]:1,[files[2]]:1});
  assert.equal(fixture.fieldsRows.length,12);assert.equal(fixture.pageRows.length,8);assert.equal(fixture.sourceAuthorities.length,3);
  assert.equal(fixture.sourceAuthorities[1].r1Failure,"THREE_HTML_ENTITY_ESCAPES_IN_OLD_SOURCE");assert.equal(fixture.sourceAuthorities[1].sameFragmentFailures,1);assert.equal(fixture.sourceAuthorities[1].r1NewAndEightRowsPreserved,true);assert.equal(fixture.workerApplicationTakeover,false);assert.equal(fixture.rootApplicationCodeAuthored,false);
});
for(const file of files)test(file+": historical Edit source equals actual GitBASE+exact edits after finite later-document staging",()=>{
  let expected=before[file];for(const edit of edits.filter(value=>value.file===file)){assert.equal(count(expected,edit.old),1);expected=expected.replace(edit.old,()=>edit.new);}
  assert.equal(physical[file],expected,"Historical source comparator excludes only the later exact document batch");
  const pins=fixture.applicationBaseline.find(value=>value.file===file);assert.equal(hash(before[file]),pins.baselineLfSha256);assert.equal(hash(physical[file]),pins.candidateLfSha256);
  assert.equal(inverse(physical[file],file),before[file]);assert.equal(inverse(before[file],file),before[file]);
  const prefix="\r\n/* CUSTOMER Facebook TikTok enhance.guard.body literal */\r\n",suffix='\r\n/* CUSTOMER media provider .portal-image-enhance literal <b>&</b> */\r\n';
  assert.equal(inverse(prefix+physical[file]+suffix,file),prefix+before[file]+suffix);assert.equal(inverse(prefix+before[file]+suffix,file),prefix+before[file]+suffix);assert.equal(inverse(prefix+suffix,file),prefix+suffix);
  assert.notEqual(inverse(physical[file]+suffix,file),before[file]);assert.ok(inverse(physical[file]+suffix,file).endsWith(suffix));assert.equal(inverse(physical[file],"customer/unrelated.txt"),physical[file]);
});
test("complete Enhance function rejects missing changed duplicate detached and wrong-next-owner variants",()=>{
  const file=files[0],current=physical[file],edit=edits.find(value=>value.file===file),next="  function renderImageUpscale(";
  for(const malformed of [current.replace(edit.new,""),current.replace(edit.new,edit.new.replace("const canViewCapability","const UNKNOWN_canViewCapability")),current+"\n"+edit.new,current.replace(edit.new,"")+"\n"+edit.new,current.replace(next,"  function UNKNOWN_NEXT("),current.replace(edit.new,edit.new.replace("  function renderImageEnhance(","  function UNKNOWN_OWNER("))])
    assert.throws(()=>inverse(malformed,file),fail);
  assert.equal(inverse(before[file],file),before[file]);assert.equal(inverse("/* unowned older portal source */",file),"/* unowned older portal source */");
});
test("all20 source rows reject missing mixed changed unknown duplicate detached reordered and owner faults",()=>{
  const file=files[1],current=physical[file];
  for(const edit of rows){
    for(const malformed of [current.replace(edit.new,""),current.replace(edit.new,()=>edit.old),current.replace(edit.new,edit.new.replace('],',',"UNKNOWN"],')),current.replace(edit.new,edit.new.replace(edit.newRow[0],edit.newRow[0]+".UNKNOWN")),current+"\n"+edit.new,current.replace(edit.new,"")+"\n"+edit.new])
      assert.throws(()=>inverse(malformed,file),fail);
  }
  const[a,b]=rows,marker="@@IMAGE_EDIT_OWNED_SWAP@@";assert.throws(()=>inverse(current.replace(a.new,marker).replace(b.new,()=>a.new).replace(marker,()=>b.new),file),fail);
  assert.throws(()=>inverse(current.replace("  const IMAGE_OPERATION_COPY_ROWS = [","  const UNKNOWN_COPY_ROWS = ["),file),fail);
  assert.throws(()=>inverse(current+"\n  const IMAGE_OPERATION_COPY_ROWS = [\n  ];",file),fail);
  const start=current.indexOf("  const IMAGE_OPERATION_COPY_ROWS = ["),end=current.indexOf("\n  ];",start);assert.ok(end>start);
  assert.throws(()=>inverse(current.slice(0,end)+current.slice(end).replace("\n  ];","\n  UNKNOWN_END;"),file),fail);
});
test("single scoped CSS append rejects changed scope maxwidth duplicate partial detached order and unknown rules",()=>{
  const file=files[2],current=physical[file],edit=edits.find(value=>value.file===file),block=edit.new.slice(edit.old.length);
  for(const altered of [block.replace("700px","701px"),block.replace(".portal-image-enhance",".portal-image-upscale"),block.replace("min-height: 44px","min-height: 43px"),block.replace("/* Compact only the manual image editor's mobile workspace navigation. */\n",""),block.slice(0,-2)])
    assert.throws(()=>inverse(current.replace(block,altered),file),fail);
  for(const malformed of [current+"\n"+block,current.replace(block,"")+"\n/* detached */"+block,current.replace(block,"")+block.split("\n").reverse().join("\n"),current+"\n.portal-image-enhance .portal-image-create-UNKNOWN { display: none; }\n"])
    assert.throws(()=>inverse(malformed,file),fail);
  assert.equal(inverse(current.replace(block,""),file),before[file],"Whole missing addition is the legitimate OLD phase");
  assert.equal(pdfInverse(current,file),before[file],"CSS reaches the new leaf before PDF's unsupported-file return");
});
for(const[locale,index]of [["vi",1],["en",2],["zh",3]]){
  const next=rows.map(row=>["imageOperationUi."+row.newRow[0],row.newRow[index]]),old=rows.map(row=>["imageOperationUi."+row.oldRow[0],row.oldRow[index]]);
  test(locale+": exact20 catalogue values map to OLD; neutral cells and arbitrary customer keys remain held",()=>{
    const first=Object.freeze(["CUSTOMER Facebook TikTok","media provider <b>&</b>"]),last=Object.freeze(["imageOperationUi.field.enhance.CUSTOMER_UNKNOWN","literal"]),entries=[first,...next,last],prior=[first,...old,last];
    for(const entry of entries)Object.freeze(entry);Object.freeze(entries);
    assert.deepEqual(snapshot(entries,locale),prior);assert.strictEqual(snapshot(entries,locale)[0],first);assert.strictEqual(snapshot(entries,locale).at(-1),last);assert.strictEqual(snapshot(prior,locale),prior);assert.strictEqual(snapshot([first,last],locale)[0],first);
    assert.deepEqual(pdfSnapshot(entries,locale),prior,"Historical composition stays after PDF's own guards");
    const neutral=rows.filter(row=>row.oldRow[index]===row.newRow[index]);if(locale!=="vi")assert.equal(neutral.length,2);else assert.equal(neutral.length,0);
  });
  test(locale+": catalogue rejects missing mixed unknown-value duplicate and reordered owned keys",()=>{
    const changed=rows.map((row,at)=>row.oldRow[index]!==row.newRow[index]?at:-1).filter(at=>at>=0);
    for(const malformed of [next.slice(1),next.slice(0,-1),[...next,next[0]],next.map((entry,at)=>at===changed[0]?[entry[0],"UNKNOWN"]:entry),next.map((entry,at)=>at===changed[0]?old[at]:entry),[next[1],next[0],...next.slice(2)],next.map((entry,at)=>at===0?[entry[0]+".UNKNOWN",entry[1]]:entry)])
      assert.throws(()=>snapshot(malformed,locale),fail);
  });
}
test("type and locale guard identity remains owned by the PDF comparator before new historical composition",()=>{
  assert.throws(()=>pdfInverse(null,files[0]),/Unreviewed PDF utilities customer copy/);
  assert.throws(()=>pdfSnapshot([],"fr"),/Unreviewed PDF utilities customer copy/);assert.throws(()=>pdfSnapshot(null,"vi"),/Unreviewed PDF utilities customer copy/);
  assert.throws(()=>inverse(null,files[0]),fail);assert.throws(()=>snapshot([],"fr"),fail);assert.throws(()=>snapshot(null,"vi"),fail);
});
