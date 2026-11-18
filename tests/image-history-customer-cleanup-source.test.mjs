import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {createHash} from "node:crypto";
import {execFileSync} from "node:child_process";
import {historyCustomerCleanupHistoricalSource as inverse,historyCustomerCleanupHistoricalSnapshot as snapshot} from "./helpers/image-history-customer-cleanup-snapshot.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),".."),BASE="7af6e2f89f99a3739d13e173b173e81e5179b969",fail=/Unreviewed History customer cleanup/,lf=value=>value.replace(/\r\n/g,"\n"),count=(source,part)=>source.split(part).length-1;
const pins=[
  ["ready-copy","4c4a2c9cf418331701f52195c092a150627375f6281bcfab0a470f14df8a3820","IMAGE-HISTORY-READY-COPY-20261118","5eee3247-8f69-48f6-8004-bfda7e287fac",8],
  ["customer-structure","2bd1a16e4bb9ff78f3344ec8f2b010ff7f23644ffb63ccf9f5f6f44f66d64673","IMAGE-HISTORY-CUSTOMER-STRUCTURE-20261118","de9c50e6-3cc8-4084-8225-a88c8d63ce01",2],
  ["outer-meta","6ecd6c9c47a0c24c0f7d059e28034f112019e4bd54f066437a063db4b27eca54","IMAGE-HISTORY-OUTER-META-20261119","98527f67-e77f-47a1-95aa-521c06aa2c58",5],
  ["refresh-feedback","d23dc6e3acd6365400205e60debad8564325d73b78af44c1253ecf8564c24d9a","IMAGE-HISTORY-REFRESH-FEEDBACK-20261119","11cba0b5-2678-4a9c-ae4e-cae51aa2479f",3],
  ["retry-label","48164df192a9a685a32159fc1819da97598be44f73ca48a2eb61b6f8d4ebcb6a","IMAGE-HISTORY-RETRY-LABEL-20261119","d524969c-a91f-409f-bc14-730f13405a9b",1]
];
const authorities=pins.map(([name])=>fs.readFileSync(new URL("./fixtures/image-history-"+name+"-reviewed.json",import.meta.url))),fixtures=authorities.map(raw=>JSON.parse(raw)),edits=fixtures.flatMap(value=>value.proposal.changes);
const files=[...new Set(edits.map(edit=>edit.file))],before=Object.fromEntries(files.map(file=>[file,lf(execFileSync("git",["show",BASE+":"+file],{cwd:root,encoding:"utf8",maxBuffer:30e6}))])),physical=Object.fromEntries(files.map(file=>[file,lf(fs.readFileSync(path.join(root,file),"utf8"))]));
const unit=edit=>edit.new.startsWith(edit.old)?edit.new.slice(edit.old.length):edit.new.endsWith(edit.old)?edit.new.slice(0,-edit.old.length):edit.new;
test("exact authority SHA/spec/conversation/count/order: READY8 STRUCTURE2 META5 FEEDBACK3 RETRY1",()=>{
  assert.equal(edits.length,19);assert.equal(files.length,4);
  for(const[index,[name,sha,spec,conversation,total]]of pins.entries()){const value=fixtures[index];assert.equal(createHash("sha256").update(authorities[index]).digest("hex"),sha,name);assert.equal(value.review.schemaValid,true);assert.equal(value.review.proposalExact,true);assert.equal(value.review.specId,spec);assert.equal(value.review.conversation,conversation);assert.equal(value.proposal.specId,spec);assert.equal(value.proposal.revision,"R1");assert.equal(value.proposal.changes.length,total);assert.ok(value.proposal.changes.every(edit=>edit.count===1));}
  assert.deepEqual(files.sort(),["copyfast_pages.py","static/portal/integration.js","static/portal/portal-i18n.js","static/portal/portal.js"].sort());
});
for(const file of files){
  test(file+": CURRENT physical source equals exactly ordered accepted changes from Git BASE",()=>{
    let expected=before[file];for(const edit of edits.filter(row=>row.file===file)){assert.equal(count(expected,edit.old),1,"count-one OLD anchor");expected=expected.replace(edit.old,()=>edit.new);}
    assert.equal(physical[file],expected,"Read candidate directly; do not normalize current acceptance");assert.equal(inverse(physical[file],file),before[file]);assert.equal(inverse(before[file],file),before[file]);
  });
  test(file+": finite inverse preserves arbitrary outside bytes and no-owned older inputs",()=>{
    const prefix='\r\n/* CUSTOMER Facebook TikTok <literal>& Lịch sử ảnh */\r\n',suffix='\r\n/* unrelated outside bytes */\r\n';
    assert.equal(inverse(prefix+physical[file]+suffix,file),prefix+before[file]+suffix);assert.equal(inverse(prefix+before[file]+suffix,file),prefix+before[file]+suffix);assert.equal(inverse(prefix+suffix,file),prefix+suffix);
  });
  test(file+": missing changed mixed duplicate detached/reordered owned edits are rejected",()=>{
    const selected=edits.filter(row=>row.file===file);
    for(const edit of selected){const part=unit(edit);assert.equal(count(physical[file],part),1);
      assert.throws(()=>inverse(physical[file].replace(part,""),file),fail,"missing");
      assert.throws(()=>inverse(physical[file].replace(part,part.slice(0,-1)+"?"),file),fail,"changed");
      assert.throws(()=>inverse(physical[file]+"\n"+part,file),fail,"duplicate");
      assert.throws(()=>inverse(physical[file].replace(part,"")+"\n"+part,file),fail,"detached");
      if(part===edit.new)assert.throws(()=>inverse(physical[file].replace(edit.new,()=>edit.old),file),fail,"mixed OLD/NEW");
    }
    const[a,b]=selected.slice(0,2).map(unit),marker="@@HISTORY_OWNED_SWAP@@";assert.equal(count(physical[file],marker),0);
    assert.throws(()=>inverse(physical[file].replace(a,marker).replace(b,()=>a).replace(marker,()=>b),file),fail,"reordered");
  });
}
const rowOrder=["history.intro.kicker","history.intro.title","history.intro.body","history.metric.count","history.results.title","history.results.description","history.retry","history.empty.title","history.empty.body"];
const rows=edits.filter(edit=>edit.file==="static/portal/portal-i18n.js"&&edit.old.trim().startsWith("[")).map(edit=>({old:JSON.parse(edit.old.trim().replace(/,$/,"")),next:JSON.parse(edit.new.trim().replace(/,$/,""))})).sort((a,b)=>rowOrder.indexOf(a.old[0])-rowOrder.indexOf(b.old[0]));
const appendEdits=edits.filter(edit=>edit.file==="static/portal/portal-i18n.js"&&edit.old.trim()==="verifyEqualKeysets();"),added={vi:[],en:[],zh:[]};
for(const edit of appendEdits)for(const block of unit(edit).matchAll(/  Object\.assign\(MESSAGES\.(vi|en|zh), \{\n([\s\S]*?)\n  \}\);/g))for(const line of block[2].split("\n")){const match=line.match(/^\s*(?:"([^"]+)"|([A-Za-z]\w*)):\s*("(?:[^"\\]|\\.)*"),?$/);assert.ok(match);added[block[1]].push([match[1]||match[2],JSON.parse(match[3])]);}
for(const[locale,index]of [["vi",1],["en",2],["zh",3]]){
  test(locale+": restore nine row values/remove five added keys; preserve unknown entries and order",()=>{
    assert.equal(rows.length,9);assert.equal(added[locale].length,5);
    const outside=[Object.freeze(["CUSTOMER Facebook TikTok","<b>literal & text</b>"]),Object.freeze(["unknown.namespace","unchanged"])],old=[outside[0],...rows.map(row=>["imageOperationUi."+row.old[0],row.old[index]]),outside[1]],next=[outside[0],...rows.map(row=>["imageOperationUi."+row.next[0],row.next[index]]),outside[1],...added[locale]];
    for(const entry of next)Object.freeze(entry);Object.freeze(next);assert.deepEqual(snapshot(next,locale),old);assert.strictEqual(snapshot(old,locale),old);assert.strictEqual(snapshot(outside,locale),outside);assert.strictEqual(snapshot(next,locale)[0],outside[0]);assert.strictEqual(snapshot(next,locale).at(-1),outside[1]);
  });
  test(locale+": catalogue rejects missing changed mixed duplicate detached/reordered owned entries",()=>{
    const old=rows.map(row=>["imageOperationUi."+row.old[0],row.old[index]]),next=[...rows.map(row=>["imageOperationUi."+row.next[0],row.next[index]]),...added[locale]],swap=values=>[values[1],values[0],...values.slice(2)];
    const malformed=[next.slice(1),next.slice(0,-1),[...next,next[0]],[...next,next.at(-1)],next.map((row,i)=>i===0?[row[0],"UNKNOWN"]:row),next.map((row,i)=>i===0?old[0]:row),swap(next),[...added[locale],...next.slice(0,9)],[...next.slice(0,9),...swap(added[locale])],next.map((row,i)=>i===9?[row[0]+".UNKNOWN",row[1]]:row),[...old,...added[locale]]];
    for(const value of malformed)assert.throws(()=>snapshot(value,locale),fail);assert.throws(()=>snapshot(next,"fr"),fail);
  });
}
