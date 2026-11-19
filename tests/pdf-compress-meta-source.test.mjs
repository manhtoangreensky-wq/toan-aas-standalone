import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {imageToPdfGuardHistoricalPortalSource} from "./helpers/image-to-pdf-guard-snapshot.mjs";
import {imageEnhanceHelpHistoricalI18nSource} from "./helpers/image-enhance-help-snapshot.mjs";
import {imageToPdfMetaHistoricalPortalSource,imageToPdfMetaHistoricalI18nSource,imageToPdfMetaHistoricalPagesSource} from "./helpers/image-to-pdf-meta-snapshot.mjs";
import {documentConvertCustomerHistoricalSource} from "./helpers/document-convert-customer-copy-snapshot.mjs";
import {
  pdfCompressMetaHistoricalPortalSource,pdfCompressMetaHistoricalI18nSource,
  pdfCompressMetaHistoricalPagesSource,pdfCompressMetaHistoricalSnapshot
} from "./helpers/pdf-compress-meta-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/pdf-compress-meta-reviewed.json",import.meta.url),"utf8"));
const edits=JSON.parse(fixture.expectedRaw),lf=value=>value.replace(/\r\n/g,"\n");
const inverses={"static/portal/portal.js":pdfCompressMetaHistoricalPortalSource,
  "static/portal/portal-i18n.js":pdfCompressMetaHistoricalI18nSource,"copyfast_pages.py":pdfCompressMetaHistoricalPagesSource};
const newer={"static/portal/portal.js":imageToPdfMetaHistoricalPortalSource,"static/portal/portal-i18n.js":imageToPdfMetaHistoricalI18nSource,"copyfast_pages.py":imageToPdfMetaHistoricalPagesSource};
test("Compress source equals five reviewed additions and preserves every other source byte",()=>{
  for(const[file,inverse]of Object.entries(inverses)){
    const baseline=lf(execFileSync("git",["show",fixture.sourceBase+":"+file],{encoding:"utf8",maxBuffer:12e6}));
    let expected=baseline;
    for(const edit of edits.filter(value=>value.file===file)){
      assert.equal(expected.split(edit.old).length-1,1);expected=expected.replace(edit.old,()=>edit.new);
    }
    const staged=documentConvertCustomerHistoricalSource(lf(fs.readFileSync(file,"utf8")),file),physical=newer[file](staged);
    const current=file==="static/portal/portal.js"?imageToPdfGuardHistoricalPortalSource(physical):file==="static/portal/portal-i18n.js"?imageEnhanceHelpHistoricalI18nSource(physical):physical;
    assert.equal(current,expected);assert.equal(inverse(current),baseline);assert.equal(inverse(baseline),baseline);
  }
});
test("Compress source inverse rejects unknown/partial/duplicate/moved additions without masking outside changes",()=>{
  for(const[file,inverse]of Object.entries(inverses)){
    // Historical source comparator only, before original negative-vector mutations.
    const staged=documentConvertCustomerHistoricalSource(lf(fs.readFileSync(file,"utf8")),file),physical=newer[file](staged);
    const source=file==="static/portal/portal.js"?imageToPdfGuardHistoricalPortalSource(physical):file==="static/portal/portal-i18n.js"?imageEnhanceHelpHistoricalI18nSource(physical):physical,selected=edits.filter(value=>value.file===file);
    const edit=selected[0],addition=file.endsWith("portal-i18n.js")?edit.new.slice(0,-edit.old.length):edit.new.slice(edit.old.length);
    const baseline=inverse(source),prefix="\r\n/* CUSTOMER Facebook TikTok */\r\n",suffix="\r\n# outside customer";
    assert.equal(inverse(prefix+source+suffix),prefix+baseline+suffix);
    assert.throws(()=>inverse(source+"\n"+addition),/Unreviewed PDF Compress/);
    assert.throws(()=>inverse(source.replace(addition,addition.replace("/documents/compress","/documents/UNKNOWN").replace("pdfCompressMetaUiTitle","pdfCompressMetaUiUNKNOWN"))),/Unreviewed PDF Compress/);
    if(selected.length>1)assert.throws(()=>inverse(source.replace(addition,"")),/Unreviewed PDF Compress/);
    assert.throws(()=>inverse(source.replace(addition,"")+"\n"+addition),/Unreviewed PDF Compress/);
  }
  const entries=[["older","outside"],["pdfCompressMetaUiTitle","Nén PDF"],
    ["pdfCompressMetaUiDescription","Giảm dung lượng PDF khi có thể. Tệp gốc được giữ nguyên."],["customer","raw"]];
  assert.deepEqual(pdfCompressMetaHistoricalSnapshot(entries,"vi"),[["older","outside"],["customer","raw"]]);
  assert.throws(()=>pdfCompressMetaHistoricalSnapshot(entries.slice(0,2),"vi"),/Unreviewed PDF Compress/);
});
