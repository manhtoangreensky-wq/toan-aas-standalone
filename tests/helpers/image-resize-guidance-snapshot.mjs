import fs from "node:fs";
import assert from "node:assert/strict";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/image-resize-guidance-reviewed.json",import.meta.url),"utf8"));
const fail="Unreviewed Image Resize guidance",locales=["vi","en","zh"];
const count=(text,part)=>text.split(part).length-1;
const order=["resize.form.description","resize.boundary.description","resize.runReason.ready"];
const ordered=order.map(key=>fixture.changes.find(edit=>JSON.parse(edit.old.trim().replace(/,$/,""))[0]===key));
assert.ok(ordered.every(Boolean),fail+" three reviewed keys");
export function imageResizeGuidanceHistoricalI18nSource(source){
  assert.equal(typeof source,"string",fail);
  const present=fixture.changes.map(edit=>({old:count(source,edit.old),next:count(source,edit.new)}));
  const keys=fixture.rows.map(row=>count(source,'["'+row.key+'",'));
  if(keys.every(n=>n===0))return source;
  assert.ok(keys.every(n=>n===1),fail+" missing/duplicate key");
  const isOld=present.every(p=>p.old===1&&p.next===0),isNew=present.every(p=>p.old===0&&p.next===1);
  assert.ok(isOld||isNew,fail+" partial/changed/moved row");
  const start=source.indexOf("  const IMAGE_OPERATION_COPY_ROWS = ["),end=source.indexOf("\n  ];",start);
  assert.ok(start>=0&&end>start,fail+" catalogue owner");
  const part=source.slice(start,end),mode=isNew?"new":"old";
  for(const edit of fixture.changes)assert.equal(count(part,edit[mode]),1,fail+" row outside owner");
  const positions=ordered.map(edit=>part.indexOf(edit[mode]));
  assert.ok(positions.every((p,index)=>index===0||p>positions[index-1]),fail+" row order");
  if(isOld)return source;
  let restored=source;
  for(const edit of fixture.changes)restored=restored.replace(edit.new,()=>edit.old);
  return restored; // Restore exactly three reviewed rows; retain every other byte and newline.
}
export function imageResizeGuidanceHistoricalSnapshot(entries,locale){
  assert.ok(locales.includes(locale),fail+" locale");
  const keys=fixture.rows.map(row=>"imageOperationUi."+row.key),index=locales.indexOf(locale);
  const found=keys.map(key=>entries.filter(([name])=>name===key));
  if(found.every(values=>values.length===0))return entries;
  assert.ok(found.every(values=>values.length===1),fail+" missing/duplicate catalogue key");
  const values=found.map(result=>result[0][1]);
  const old=fixture.rows.map(row=>row.old[index]),next=fixture.rows.map(row=>row.new[index]);
  const isOld=values.every((v,i)=>v===old[i]),isNew=values.every((v,i)=>v===next[i]);
  assert.ok(isOld||isNew,fail+" partial/unknown catalogue values");
  const orderedKeys=ordered.map(edit=>"imageOperationUi."+JSON.parse(edit.old.trim().replace(/,$/,""))[0]);
  const positions=orderedKeys.map(key=>entries.findIndex(([name])=>name===key));
  assert.ok(positions.every((p,i)=>i===0||p>positions[i-1]),fail+" catalogue row order");
  if(isOld)return entries;
  return entries.map(([key,value])=>{const position=keys.indexOf(key);return position<0?[key,value]:[key,old[position]];});
}
