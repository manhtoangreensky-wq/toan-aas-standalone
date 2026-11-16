import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import {pdfInputFont16HistoricalCss} from "./pdf-input-font16-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/pdf-customer-cleanup-reviewed.json",import.meta.url),"utf8"));
const edits=fixture.changes,ready=edits.slice(0,8),reference=edits.slice(-11),amendments=edits.slice(8,-11);
const portal="static/portal/portal.js",i18n="static/portal/portal-i18n.js",theme="static/portal/portal-theme.css";
const owners=["renderPdfSplit","renderPdfMerge","renderPdfOptimize"],locales=["vi","en","zh"],keys=Object.keys(fixture.vi);
const fail="Unreviewed PDF customer cleanup",count=(value,needle)=>value.split(needle).length-1;
const hash=value=>createHash("sha256").update(value).digest("hex");
assert.equal(keys.length,19);assert.equal(new Set(keys).size,19);assert.ok(keys.every(key=>key.startsWith("docPdfReadyUi")));
assert.deepEqual(ready.map(edit=>edit.file),[portal,portal,portal,portal,portal,portal,i18n,theme]);
assert.deepEqual(reference.map(edit=>edit.file),[portal,portal,portal,portal,i18n,i18n,i18n,i18n,i18n,i18n,theme]);
assert.ok(amendments.every(edit=>[portal,i18n].includes(edit.file)));
for(const edit of edits){assert.equal(edit.count,1);assert.equal(typeof edit.old,"string");assert.equal(typeof edit.new,"string");assert.ok(edit.old&&edit.new&&edit.old!==edit.new);}
for(const locale of locales){assert.deepEqual(Object.keys(fixture[locale]),keys);assert.equal(fixture.reference.catalogEntries[locale].length,6);}
function once(source,old,next){assert.equal(count(source,old),1,fail+" missing/changed/duplicate chunk");return source.replace(old,()=>next);}
function scoped(source,name,old,next){
  const anchor="  function "+name+"(";assert.equal(count(source,anchor),1,fail+" owner");
  const start=source.indexOf(anchor),end=source.indexOf("\n  function ",start+anchor.length);
  assert.ok(end>start,fail+" function boundary");
  return source.slice(0,start)+once(source.slice(start,end),old,next)+source.slice(end);
}
const portalSignal=source=>/docPdfReadyUi|portal-document-operation-layout--single|imageOperationText\("reference\.(?:range", "\{label\}: \{start\}–\{end\}|aria", "Trang tệp|title", "Tìm \{type\} trong kho tệp|loading", "Đang tải tệp…|failed", "Chưa tải được tệp)/.test(source);
export function pdfCustomerCleanupHistoricalPortalSource(source){
  assert.equal(typeof source,"string",fail);
  if(!portalSignal(source))return source; // Older historical sources need no unrelated baseline chunks.
  let value=source;
  for(const edit of reference.slice(0,4).reverse())value=once(value,edit.new,edit.old);
  for(const edit of amendments.filter(edit=>edit.file===portal).reverse())value=scoped(value,"renderPdfOptimize",edit.new,edit.old);
  for(const text of new Set(ready.slice(0,6).map(edit=>edit.new)))
    assert.equal(count(value,text),ready.slice(0,6).filter(edit=>edit.new===text).length,fail+" misplaced/duplicate READY");
  for(let index=5;index>=0;index--)value=scoped(value,owners[Math.floor(index/2)],ready[index].new,ready[index].old);
  assert.equal(portalSignal(value),false,fail+" partial/unknown residual code");
  return value; // No newline conversion or whole-function masking.
}
export function pdfCustomerCleanupHistoricalI18nSource(source){
  assert.equal(typeof source,"string",fail);
  const signals=source.includes("docPdfReadyUi")||reference.slice(4,10).some(edit=>source.includes(edit.new));
  if(!signals)return source;
  let value=source;
  for(const edit of reference.slice(4,10).reverse())value=once(value,edit.new,edit.old);
  for(const edit of amendments.filter(edit=>edit.file===i18n).reverse())value=once(value,edit.new,edit.old);
  value=once(value,ready[6].new,ready[6].old);
  assert.equal(value.includes("docPdfReadyUi"),false,fail+" unknown/residual catalogue");
  return value;
}
export function pdfCustomerCleanupHistoricalSnapshot(entries,locale){
  assert.ok(locales.includes(locale),fail+" locale");
  const added=entries.filter(([key])=>key.startsWith("docPdfReadyUi"));
  let result=entries;
  if(added.length){
    assert.deepEqual(added,Object.entries(fixture[locale]),fail+" missing/unknown/value/order/duplicate READY key");
    assert.deepEqual(entries.slice(-keys.length),added,fail+" READY keys must append");
    assert.equal(hash(JSON.stringify(added)),fixture.binding.catalogHashes[locale],fail+" READY catalogue hash");
    result=entries.slice(0,-keys.length);
  }
  const expected=fixture.reference.catalogEntries[locale],refKeys=new Set(expected.map(entry=>entry.key));
  const existing=result.filter(([key])=>refKeys.has(key));
  if(!existing.length){assert.equal(added.length,0,fail+" missing reference rows");return result;}
  assert.deepEqual(existing.map(([key])=>key),expected.map(entry=>entry.key),fail+" missing/duplicate/reference order");
  const old=expected.every((entry,index)=>existing[index][1]===entry.old);
  const current=expected.every((entry,index)=>existing[index][1]===entry.new);
  assert.ok(old||current,fail+" partial/unknown reference values");
  if(added.length)assert.ok(current,fail+" partial READY/reference catalogue");
  // Both known complete row states are supported for earlier snapshot consumers; never reorder entries.
  return result.map(([key,value])=>[key,current&&refKeys.has(key)?expected.find(entry=>entry.key===key).old:value]);
}
export const PDF_CUSTOMER_CLEANUP_READY_CSS_PREFIX=ready[7].new.slice(0,-ready[7].old.length);
export const PDF_CUSTOMER_CLEANUP_REFERENCE_CSS_PREFIX=reference[10].new.slice(0,-reference[10].old.length);
export function pdfCustomerCleanupHistoricalCss(source){
  assert.equal(typeof source,"string",fail+" CSS");
  source=pdfInputFont16HistoricalCss(source);
  const has=/Keep PDF forms focused on the selected task|portal-document-operation-layout--single|Keep source-file search labels and navigation readable|\.portal-operation-reference-picker \.portal-operation-reference-copy/.test(source);
  if(!has)return source;
  assert.ok(ready[7].new.endsWith(ready[7].old)&&reference[10].new.endsWith(reference[10].old),fail+" CSS prepend contract");
  const combined=PDF_CUSTOMER_CLEANUP_READY_CSS_PREFIX+reference[10].new;
  assert.equal(count(source,combined),1,fail+" CSS partial/misplaced/changed prefixes");
  let value=once(source,reference[10].new,reference[10].old);
  value=once(value,ready[7].new,ready[7].old);
  assert.equal(/Keep PDF forms focused on the selected task|portal-document-operation-layout--single|Keep source-file search labels and navigation readable|\.portal-operation-reference-picker \.portal-operation-reference-copy/.test(value),false,fail+" CSS duplicate/unknown residual");
  return value; // Preserve original Split + Compress and all outside bytes, including mixed CRLF.
}
