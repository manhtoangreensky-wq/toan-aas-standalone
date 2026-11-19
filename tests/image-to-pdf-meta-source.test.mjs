import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {imageToPdfMetaHistoricalPortalSource,imageToPdfMetaHistoricalI18nSource,imageToPdfMetaHistoricalPagesSource,imageToPdfMetaHistoricalSnapshot} from "./helpers/image-to-pdf-meta-snapshot.mjs";
import {imageEnhanceMetaHistoricalPortalSource,imageEnhanceMetaHistoricalI18nSource,imageEnhanceMetaHistoricalPagesSource} from "./helpers/image-enhance-meta-snapshot.mjs";
import {documentConvertCustomerHistoricalSource} from "./helpers/document-convert-customer-copy-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/image-to-pdf-meta-reviewed.json",import.meta.url),"utf8")),edits=fixture.proposal.changes;
const base="c584e4f80db09b5418b104cbc1629d5e322fd8d4",lf=value=>value.replace(/\r\n/g,"\n");
const inverses={"static/portal/portal.js":imageToPdfMetaHistoricalPortalSource,"static/portal/portal-i18n.js":imageToPdfMetaHistoricalI18nSource,"copyfast_pages.py":imageToPdfMetaHistoricalPagesSource};
const newer={"static/portal/portal.js":imageEnhanceMetaHistoricalPortalSource,"static/portal/portal-i18n.js":imageEnhanceMetaHistoricalI18nSource,"copyfast_pages.py":imageEnhanceMetaHistoricalPagesSource};
test("Image-to-PDF metadata source equals five exact additions with every outside byte unchanged",()=>{
  for(const[file,inverse]of Object.entries(inverses)){
    const before=lf(execFileSync("git",["show",base+":"+file],{encoding:"utf8",maxBuffer:12e6}));let expected=before;
    for(const edit of edits.filter(row=>row.file===file)){assert.equal(edit.count,1);assert.equal(expected.split(edit.old).length-1,1);expected=expected.replace(edit.old,()=>edit.new);}
    const staged=documentConvertCustomerHistoricalSource(lf(fs.readFileSync(file,"utf8")),file),current=newer[file](staged);assert.equal(current,expected);assert.equal(inverse(current),before);assert.equal(inverse(before),before);
  }
});
test("Image-to-PDF metadata inverses reject partial/unknown/duplicate/moved changes and preserve customer bytes",()=>{
  for(const[file,inverse]of Object.entries(inverses)){
    // Source-only DCC staging happens before these unchanged malformed historical vectors.
    const staged=documentConvertCustomerHistoricalSource(lf(fs.readFileSync(file,"utf8")),file),source=newer[file](staged),selected=edits.filter(row=>row.file===file),edit=selected[0];
    const part=file.endsWith("portal-i18n.js")?edit.new.slice(0,-edit.old.length):edit.new.slice(edit.old.length);
    const prefix="\r\n/* CUSTOMER Facebook TikTok */\r\n",suffix="\r\n/* outside */";
    assert.equal(inverse(prefix+source+suffix),prefix+inverse(source)+suffix);
    assert.throws(()=>inverse(source+"\n"+part),/Unreviewed Image-to-PDF metadata/);
    assert.throws(()=>inverse(source.replace(part,part.replace("/documents/image-to-pdf","/documents/UNKNOWN").replace("imageToPdfMetaUiTitle","imageToPdfMetaUiUNKNOWN"))),/Unreviewed Image-to-PDF metadata/);
    if(selected.length>1)assert.throws(()=>inverse(source.replace(part,"")),/Unreviewed Image-to-PDF metadata/);
    assert.throws(()=>inverse(source.replace(part,"")+"\n"+part),/Unreviewed Image-to-PDF metadata/);
  }
  const entries=[["customer","literal"],["imageToPdfMetaUiTitle","Ảnh thành PDF"],["imageToPdfMetaUiDescription","Chọn ảnh và ghép thành một tệp PDF. Ảnh gốc được giữ nguyên."]];
  assert.deepEqual(imageToPdfMetaHistoricalSnapshot(entries,"vi"),[entries[0]]);
  assert.throws(()=>imageToPdfMetaHistoricalSnapshot(entries.slice(0,2),"vi"),/Unreviewed Image-to-PDF metadata/);
});
