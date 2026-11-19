import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {pdfUtilitiesCustomerHistoricalSource as inverse,pdfUtilitiesCustomerHistoricalSnapshot as snapshot} from "./helpers/pdf-utilities-customer-copy-snapshot.mjs";
import {imageEditCustomerHistoricalSource} from "./helpers/image-edit-customer-copy-snapshot.mjs";
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),".."),BASE="513557a9ece0f8fe049884868dc5fb3a1ac2339c";
const raw=fs.readFileSync(new URL("./fixtures/pdf-utilities-customer-copy-reviewed.json",import.meta.url)),fixture=JSON.parse(raw),edits=fixture.canonicalChanges,fail=/Unreviewed PDF utilities customer copy/;
const lf=value=>value.replace(/\r\n/g,"\n"),count=(source,part)=>source.split(part).length-1,hash=value=>createHash("sha256").update(value).digest("hex");
const files=["static/portal/portal.js","static/portal/portal-i18n.js"],before=Object.fromEntries(files.map(file=>[file,lf(execFileSync("git",["show",BASE+":"+file],{cwd:ROOT,encoding:"utf8",maxBuffer:30e6}))])),physical=Object.fromEntries(files.map(file=>[file,lf(fs.readFileSync(path.join(ROOT,file),"utf8"))]));
// Historical PDF source comparator only: remove the separately reviewed later Edit batch, never a current renderer.
const historical=Object.fromEntries(files.map(file=>[file,imageEditCustomerHistoricalSource(physical[file],file)]));
test("exact immutable authority, all four canonical edits and 15 translated rows; Root faults do not change AGY counters",()=>{
  assert.equal(hash(raw),"fb1ffa41f9d924a11caf78b840d5ebc2a8e6a270eb49e91838868def71973870");assert.equal(fixture.base,BASE);assert.equal(fixture.task,"PDF-UTILITIES-CUSTOMER-COPY-20261119");assert.equal(fixture.revision,"ROOT_REVIEWED_R1_WITH_SPEC_AMENDMENTS");
  assert.equal(edits.length,4);assert.deepEqual(edits.map(edit=>edit.file),[files[0],files[0],files[0],files[1]]);assert.ok(edits.every(edit=>edit.count===1));assert.equal(fixture.fieldsRows.length,6);assert.equal(fixture.pageRows.length,9);
  assert.deepEqual(fixture.sourceAuthorities.map(value=>[value.specId,value.revision,value.conversation]),[
    ["PDF-COMPRESS-NOTES-CLEANUP-20261119","R1","ce980f42-58d0-422d-ae04-d61e3a1fc290"],
    ["IMAGE-TO-PDF-FIELD-LOCALE-20261119","R1","b601f267-e64d-4316-bece-787471d5309e"],
    ["IMAGE-TO-PDF-PAGE-CUSTOMER-CLEANUP-20261119","R1","d1246c74-da84-4150-812d-c5463f5c42c9"]]);
  assert.ok(fixture.sourceAuthorities.every(value=>value.sourceProposalExact&&value.amendedSchemaValid));assert.equal(fixture.rootSpecAmendments.workerApplicationFailureCount,0);assert.equal(fixture.sourceAuthorities[2].recovery.partialValuesRepaired,false);assert.equal(fixture.sourceAuthorities[2].recovery.applicationFailureCount,0);
});
for(const file of files){
  test(file+": historical PDF candidate equals exact canonical changes from actual Git BASE; inverse preserves every outside byte",()=>{
    let expected=before[file];for(const edit of edits.filter(value=>value.file===file)){assert.equal(count(expected,edit.old),1);expected=expected.replace(edit.old,()=>edit.new);}
    assert.equal(historical[file],expected,"Historical PDF source comparator excludes only the later exact Edit batch");
    const pins=fixture.applicationBaseline.find(value=>value.file===file);assert.equal(hash(before[file]),pins.baselineLfSha256);assert.equal(hash(historical[file]),pins.candidateLfSha256);
    assert.equal(inverse(historical[file],file),before[file]);assert.equal(inverse(before[file],file),before[file]);
    const prefix="\r\n/* CUSTOMER Facebook TikTok docImageToPdfFieldLabel outside literal */\r\n",suffix='\r\nconst customerCopy = "portal-state-meta media provider <b>literal &</b>";\r\n';
    assert.equal(inverse(prefix+historical[file]+suffix,file),prefix+before[file]+suffix);assert.equal(inverse(prefix+before[file]+suffix,file),prefix+before[file]+suffix);assert.equal(inverse(prefix+suffix,file),prefix+suffix);
    const outsideChange=historical[file]+suffix;assert.notEqual(inverse(outsideChange,file),before[file]);assert.ok(inverse(outsideChange,file).endsWith(suffix));
  });
}
test("portal leaf rejects missing/changed/mixed/duplicate/detached/reordered complete functions and next-owner faults",()=>{
  const file=files[0],current=historical[file],selected=edits.filter(edit=>edit.file===file);
  for(const edit of selected){
    assert.equal(count(current,edit.new),1);
    for(const malformed of [current.replace(edit.new,""),current.replace(edit.new,()=>edit.old),current.replace(edit.new,edit.new.replace("const canView","const UNKNOWN_canView").replace("const position","const UNKNOWN_position")),current+"\n"+edit.new,current.replace(edit.new,"")+"\n"+edit.new])
      assert.throws(()=>inverse(malformed,file),fail);
    const name=edit.new.match(/^  function (\w+)\(/)[1],next="  function "+fixture.nextOwners[name]+"(";
    assert.throws(()=>inverse(current.replace(next,"  function UNKNOWN_NEXT("),file),fail);
  }
  const[a,b]=[selected[1].new,selected[0].new],marker="@@PDF_OWNED_SWAP@@";
  assert.throws(()=>inverse(current.replace(a,marker).replace(b,()=>a).replace(marker,()=>b),file),fail);
});
test("i18n leaf rejects partial changed duplicate detached reordered or post-freeze catalogue without weakening keyset/freeze",()=>{
  const file=files[1],current=historical[file],edit=edits[3],chunk=edit.new.slice(0,-edit.old.length);
  for(const malformed of [current.replace(chunk,""),current.replace(chunk,chunk.replace("docImageToPdfFieldLabel","docImageToPdfFieldUNKNOWN")),current+"\n"+edit.new,current.replace(chunk,"")+"\n"+chunk,current.replace(chunk,chunk.split("\n").reverse().join("\n"))]){
    if(malformed!==before[file])assert.throws(()=>inverse(malformed,file),fail);
  }
  assert.throws(()=>inverse(current.replace(edit.new,edit.new.replace("verifyEqualKeysets();","UNKNOWN_KEYSET();")),file),fail);
  assert.throws(()=>inverse(current.replace("  deepFreeze(MESSAGES);","  UNKNOWN_FREEZE(MESSAGES);"),file),fail);
  assert.throws(()=>inverse(current.replace(chunk,"").replace("  deepFreeze(MESSAGES);","  deepFreeze(MESSAGES);\n"+chunk),file),fail);
  assert.throws(()=>inverse(current.replace(chunk,chunk+'\n  Object.assign(MESSAGES.vi, {"docImageToPdfUnknown":"UNKNOWN"});\n'),file),fail);
});
for(const[locale,index]of [["vi",1],["en",2],["zh",3]]){
  const rows=[...fixture.fieldsRows,...fixture.pageRows],added=rows.map(row=>[row[0],row[index]]);
  test(locale+": catalogue removes only exact 15 keys/values/order; unknown entries and input identities stay held",()=>{
    const first=Object.freeze(["CUSTOMER Facebook TikTok","<b>literal & text</b>"]),last=Object.freeze(["unknown.docImageToPdfFieldLabel","CUSTOMER"]),old=[first,last],current=[first,...added,last];for(const entry of current)Object.freeze(entry);Object.freeze(current);
    assert.deepEqual(snapshot(current,locale),old);assert.strictEqual(snapshot(current,locale)[0],first);assert.strictEqual(snapshot(current,locale)[1],last);assert.strictEqual(snapshot(old,locale),old);assert.strictEqual(snapshot([],locale).length,0);
  });
  test(locale+": catalogue rejects missing unknown changed duplicate and reordered owned entries",()=>{
    const malformed=[added.slice(1),added.slice(0,-1),[...added,added[0]],[...added,["docImageToPdfUnknown","UNKNOWN"]],added.map((row,i)=>i===0?[row[0],"UNKNOWN"]:row),[added[1],added[0],...added.slice(2)]];
    for(const value of malformed)assert.throws(()=>snapshot(value,locale),fail);assert.throws(()=>snapshot(added,"fr"),fail);
  });
}
