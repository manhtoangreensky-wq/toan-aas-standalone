import fs from "node:fs";
import assert from "node:assert/strict";
import {resizePlainHistoricalI18nSource,resizePlainHistoricalSnapshot} from "./image-resize-plain-copy-snapshot.mjs";
import {imageSharedHistoricalPortalSource} from "./image-shared-plain-copy-snapshot.mjs";
import {resizeControlHeightHistoricalThemeSource} from "./image-resize-control-height-snapshot.mjs";
import {pdfCompressMetaHistoricalPagesSource} from "./pdf-compress-meta-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/image-resize-polish-reviewed.json",import.meta.url),"utf8"));
const failure="Unreviewed Image Resize polish",prefix="imageResizeMetaUi",locales=["vi","en","zh"];
const count=(source,part)=>source.split(part).length-1;
const editsFor=file=>fixture.changes.filter(e=>e.file===file);
const once=(source,old,next)=>{assert.equal(count(source,old),1,failure+" missing/changed/duplicate chunk");return source.replace(old,()=>next);};
export function resizePolishHistoricalPortalSource(source){
  source=imageSharedHistoricalPortalSource(source);
  assert.equal(typeof source,"string",failure);
  const edits=editsFor("static/portal/portal.js"),footer=edits.find(e=>e.new==="");
  if(!source.includes(prefix)){
    if(!source.includes("  function renderImageResize("))return source;
    assert.equal(count(source,footer.old),1,failure+" partial footer");return source;
  }
  let restored=source;
  for(const[index,edit]of edits.filter(e=>e.new).entries()){
    const signature=index===0?"  function localizedPageTitle(":"  function localizedPageDescription(";
    const start=restored.indexOf(signature),end=restored.indexOf("\n  function ",start+signature.length);
    assert.ok(start>=0&&end>start,failure+" owner");
    assert.equal(count(restored,edit.new),1,failure+" moved/duplicate metadata");
    restored=restored.slice(0,start)+once(restored.slice(start,end),edit.new,edit.old)+restored.slice(end);
  }
  assert.equal(restored.includes(prefix),false,failure+" unknown/partial metadata");
  assert.equal(count(restored,footer.old),0,failure+" footer not removed");
  const anchor="    </article>`;\n  }\n\n  function renderImageEnhance(";
  const start=restored.indexOf("  function renderImageResize("),end=restored.indexOf(anchor,start);
  assert.ok(start>=0&&end>start,failure+" footer owner");
  return restored.slice(0,end)+footer.old+restored.slice(end);
}
export function resizePolishHistoricalI18nSource(source){
  source=resizePlainHistoricalI18nSource(source);
  assert.equal(typeof source,"string",failure);if(!source.includes(prefix))return source;
  const edit=editsFor("static/portal/portal-i18n.js")[0],restored=once(source,edit.new,edit.old);
  assert.equal(restored.includes(prefix),false,failure+" partial/unknown catalogue");return restored;
}
export function resizePolishHistoricalPagesSource(source){
  source=pdfCompressMetaHistoricalPagesSource(source);
  assert.equal(typeof source,"string",failure);const edits=editsFor("copyfast_pages.py"),found=edits.map(e=>count(source,e.new));
  if(found.every(n=>n===0)){
    for(const edit of edits){const start=source.indexOf(edit.old),end=source.indexOf("\n}",start);assert.ok(start>=0&&end>start,failure+" dictionary owner");
      assert.equal(source.slice(start,end).includes('"/image/resize":'),false,failure+" partial/unknown shell entry");}
    return source;
  }
  assert.ok(found.every(n=>n===1),failure+" partial/duplicate shell entries");
  return edits.reduce((value,e)=>once(value,e.new,e.old),source);
}
export function resizePolishHistoricalThemeSource(source){
  source=resizeControlHeightHistoricalThemeSource(source);
  assert.equal(typeof source,"string",failure);const edit=editsFor("static/portal/portal-theme.css")[0];
  if(!source.includes("/* Keep Resize field names and guidance readable in the light theme. */")){
    assert.equal(source.includes(".portal-page.portal-image-resize .portal-field > label"),false,failure+" partial light selector");return source;
  }
  return once(source,edit.new,edit.old);
}
export function resizePolishHistoricalSnapshot(entries,locale){
  entries=resizePlainHistoricalSnapshot(entries,locale);
  assert.ok(locales.includes(locale),failure+" locale");const added=entries.filter(([key])=>key.startsWith(prefix));
  if(!added.length)return entries;
  const expected=fixture.rows.map(row=>[row[0],row[locales.indexOf(locale)+1]]);
  assert.deepEqual(added,expected,failure+" catalogue keys/order/values");
  const keys=new Set(expected.map(([key])=>key));return entries.filter(([key])=>!keys.has(key));
}
